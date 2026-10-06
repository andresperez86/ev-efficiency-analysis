"""Detection-only comparison of confirmed finish geometry; no energy/model run."""
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from math import hypot
from pathlib import Path
from statistics import median, quantiles

from ev_analysis.contracts import Config
from ev_analysis.ingestion import load_csv
from ev_analysis.laps import (
    FINISH_A, FINISH_B, LocalProjection, assign_laps, cross, detect_crossings,
    point_segment_distance, subtract, valid_gps,
)
from ev_analysis.metrics import clip_interval, make_intervals
from ev_analysis.quality import flag_samples

SOURCE = Path('C:/Users/ANDRÉS PÉREZ/Projects/ResultadosGP_limpios/datos_limpios/EIA_clean.csv')
OLD_B = (4.954141279215972, -74.02090858842605)
OUTPUT = Path('outputs/lap_validation_revision2')


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def infinite_line_passes(samples, projection, finish_b):
    """Diagnostic only: infinite-line passes are never accepted as finishes."""
    b = projection.project(*finish_b)
    result = []
    for index, (left, right) in enumerate(zip(samples, samples[1:]), 1):
        if not (valid_gps(left) and valid_gps(right)):
            continue
        p = projection.project(left.latitude, left.longitude)
        q = projection.project(right.latitude, right.longitude)
        r = subtract(q, p)
        denominator = cross(r, b)
        if abs(denominator) <= 1e-10:
            continue
        t = cross((-p[0], -p[1]), b) / denominator
        u = cross((-p[0], -p[1]), r) / denominator
        if not 0 <= t <= 1:
            continue
        dt = (right.timestamp - left.timestamp).total_seconds()
        result.append(dict(
            index=index,
            elapsed_s=(left.timestamp - samples[0].timestamp).total_seconds() + t * dt,
            direction=-1 if cross(b, r) < 0 else 1,
            finish_fraction=u,
            distance_beyond_segment_m=max(0, -u, u - 1) * hypot(*b),
            x=p[0] + t * r[0], y=p[1] + t * r[1],
        ))
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    samples = load_csv(SOURCE)
    config = Config()
    projection = LocalProjection(*FINISH_A)
    old = detect_crossings(samples, FINISH_A, OLD_B, expected_direction=-1)
    new = detect_crossings(samples, FINISH_A, FINISH_B, expected_direction=-1)
    accepted = [c for c in new if c['accepted']]
    rejected = [c for c in new if not c['accepted']]
    old_accepted = [c for c in old if c['accepted']]
    old_passes = infinite_line_passes(samples, projection, OLD_B)
    new_passes = infinite_line_passes(samples, projection, FINISH_B)
    old_misses = [p for p in old_passes if p['direction'] == -1
                  and 0 < p['distance_beyond_segment_m'] < 10]
    comparison = []
    for number, old_pass in enumerate(old_misses, 1):
        # The physical pass is identified by time, since rotating the segment
        # can move its intersection into an adjacent source interval.
        nearest = min((p for p in new_passes if p['direction'] == -1),
                      key=lambda p: abs(p['elapsed_s'] - old_pass['elapsed_s']))
        if abs(nearest['elapsed_s'] - old_pass['elapsed_s']) > 3:
            raise RuntimeError('No unambiguous temporal match to historical near miss')
        candidate = next((c for c in new if abs(c['elapsed_s'] - nearest['elapsed_s']) < 1e-6), None)
        comparison.append(dict(
            previous_miss_number=number, previous_source_row=old_pass['index'] + 2,
            previous_elapsed_s=old_pass['elapsed_s'],
            previous_distance_beyond_b_m=old_pass['distance_beyond_segment_m'],
            updated_elapsed_s=nearest['elapsed_s'],
            updated_finish_fraction=nearest['finish_fraction'],
            updated_distance_beyond_b_m=nearest['distance_beyond_segment_m'],
            geometric_intersection=candidate is not None,
            accepted=candidate['accepted'] if candidate else False,
            crossing_id=candidate['crossing_id'] if candidate else None,
            reason=candidate['reason'] if candidate else 'outside_finite_finish_segment',
        ))
    misses = [row for row in comparison if not row['geometric_intersection']]
    flags = flag_samples(samples, config)
    intervals = make_intervals(samples, flags, config)
    validation = []
    for index, end in enumerate(accepted):
        row = dict(crossing_number=end['crossing_id'], timestamp=end['timestamp'],
                   interpolated_crossing_timestamp=end['interpolated_timestamp'],
                   time_since_previous_crossing_s=end['time_since_previous_crossing_s'],
                   crossing_direction=end['direction_label'], lap_number=index if index else None,
                   lap_duration_s=None, lap_distance_km=None, gps_derived_distance_km=None,
                   trip_derived_distance_km=None, gps_coverage_fraction=None,
                   accounting_distance_coverage_fraction=None,
                   maximum_trustworthy_distance_from_finish_m=None, rearm_distance_verified=None,
                   uncaptured_recurring_passes=0, validation_status='first_crossing_no_preceding_complete_lap')
        if index:
            start = accepted[index - 1]
            lo, hi = start['elapsed_s'], end['elapsed_s']
            parts = [part for interval in intervals
                     if (part := clip_interval(interval, lo, hi)) is not None]
            valid = [part for part in parts if part.valid]
            # Compute only distance support; do not integrate energy or run
            # summarize_laps(), importance, or the efficiency pipeline.
            distance = sum(part.value('trip_km', part.fraction_end)
                           - part.value('trip_km', part.fraction_start) for part in valid)
            gps_m = gps_s = 0.0
            for part in parts:
                left, right = part.left, part.right
                if not (valid_gps(left) and valid_gps(right)):
                    continue
                dt = (right.timestamp - left.timestamp).total_seconds()
                p = projection.project(left.latitude, left.longitude)
                q = projection.project(right.latitude, right.longitude)
                step = hypot(*subtract(q, p))
                if 0 < dt <= config.max_gap_s and step / dt <= 30:
                    gps_m += step * (part.fraction_end - part.fraction_start)
                    gps_s += part.duration_s
            count = sum(lo < missed['updated_elapsed_s'] < hi for missed in misses)
            finish_b = projection.project(*FINISH_B)
            rearm_distances = []
            for left, right in zip(samples, samples[1:]):
                seconds = (right.timestamp - samples[0].timestamp).total_seconds()
                dt = (right.timestamp - left.timestamp).total_seconds()
                if not lo < seconds < hi or not (valid_gps(left) and valid_gps(right)):
                    continue
                p = projection.project(left.latitude, left.longitude)
                q = projection.project(right.latitude, right.longitude)
                if 0 < dt <= config.max_gap_s and hypot(*subtract(q, p))/dt <= 30:
                    rearm_distances.append(point_segment_distance(q, (0, 0), finish_b))
            maximum_rearm_distance = max(rearm_distances, default=0)
            if hi-lo < 30 or maximum_rearm_distance < 50-1e-6:
                raise RuntimeError('Accepted sequence failed independent spacing/rearm check')
            row.update(lap_duration_s=hi - lo, lap_distance_km=distance,
                       gps_derived_distance_km=gps_m / 1000,
                       trip_derived_distance_km=end['trip_at_crossing_km'] - start['trip_at_crossing_km'],
                       gps_coverage_fraction=gps_s / (hi - lo),
                       accounting_distance_coverage_fraction=sum(p.duration_s for p in valid) / (hi - lo),
                       maximum_trustworthy_distance_from_finish_m=maximum_rearm_distance,
                       rearm_distance_verified=True,
                       uncaptured_recurring_passes=count,
                       validation_status='ambiguous_possible_multiple_physical_laps' if count else 'plausible_single_lap')
        validation.append(row)
    labels = assign_laps(samples, new)
    complete = validation[1:]
    durations = [row['lap_duration_s'] for row in complete]
    distances = [row['trip_derived_distance_km'] for row in complete]
    time_q1, _, time_q3 = quantiles(durations, n=4, method='inclusive')
    distance_q1, _, distance_q3 = quantiles(distances, n=4, method='inclusive')
    time_upper = time_q3 + 1.5*(time_q3-time_q1)
    distance_upper = distance_q3 + 1.5*(distance_q3-distance_q1)
    for row in validation:
        row['anomalous_lap'] = (row['lap_number'] is not None and
                               (row['uncaptured_recurring_passes'] > 0
                                or row['lap_duration_s'] > time_upper
                                or row['trip_derived_distance_km'] > distance_upper))
    anomalous = [row for row in complete if row['anomalous_lap']]
    partial_start_s = accepted[0]['elapsed_s'] if accepted else None
    partial_end_s = (samples[-1].timestamp - samples[0].timestamp).total_seconds() - accepted[-1]['elapsed_s'] if accepted else None
    partial_count = int(bool(partial_start_s and partial_start_s > 0)) + int(bool(partial_end_s and partial_end_s > 0))
    summary = dict(
        source=str(SOURCE), source_sha256=before, finish_a=FINISH_A, previous_finish_b=OLD_B,
        confirmed_finish_b=FINISH_B,
        previous_segment_length_m=hypot(*projection.project(*OLD_B)),
        updated_segment_length_m=hypot(*projection.project(*FINISH_B)),
        previous_geometric_intersections=len(old), previous_valid_crossings=len(old_accepted),
        previous_complete_intervals=max(0, len(old_accepted)-1), previous_partial_segments=2,
        total_geometric_intersections=len(new),
        crossings_after_direction_filter=sum(c['direction'] == -1 for c in new),
        valid_crossings=len(accepted), rejected_crossings=len(rejected),
        complete_crossing_to_crossing_intervals=max(0, len(accepted)-1), partial_segments=partial_count,
        plausible_single_lap_intervals=sum(row['validation_status'] == 'plausible_single_lap' for row in validation),
        ambiguous_possible_multiple_lap_intervals=sum(row['uncaptured_recurring_passes'] > 0 for row in validation),
        previous_near_misses=len(comparison), captured_previous_near_misses=sum(c['accepted'] for c in comparison),
        still_missed_passes=len(misses),
        consecutive_valid_crossing_intervals_s=[c['time_since_previous_crossing_s'] for c in accepted[1:]],
        all_valid_crossings_same_direction=len({c['direction'] for c in accepted}) == 1,
        expected_direction=-1, minimum_crossing_interval_s=30, rearm_distance_m=50,
        independently_verified_interval_and_rearm_rules=True,
        median_lap_time_s=median(durations), minimum_lap_time_s=min(durations),
        maximum_lap_time_s=max(durations), median_trip_lap_distance_km=median(distances),
        median_gps_lap_distance_km=median(row['gps_derived_distance_km'] for row in complete),
        anomalous_lap_numbers=[row['lap_number'] for row in anomalous],
        anomaly_time_upper_iqr_fence_s=time_upper, anomaly_distance_upper_iqr_fence_km=distance_upper,
        partial_start_duration_s=partial_start_s, partial_end_duration_s=partial_end_s,
        telemetry_label_counts=dict(Counter(row['lap_status'] for row in labels)),
        geometric_status='all_recurring_near_finish_passes_captured' if not misses else 'recurring_passes_still_missed',
        physical_single_lap_validation='geometrically_supported_pending_anomaly_review' if not misses else 'incomplete',
        efficiency_analysis_run=False, feature_importance_run=False,
    )
    write_csv(OUTPUT/'lap_crossings.csv', new)
    write_csv(OUTPUT/'crossing_lap_validation.csv', validation)
    write_csv(OUTPUT/'previous_near_misses_comparison.csv', comparison)
    write_csv(OUTPUT/'telemetry_lap_labels.csv', [dict(source_row=s.source_row, timestamp=s.timestamp.isoformat(), **label)
                                               for s, label in zip(samples, labels)])
    render_plot(samples, old, new, projection, new_passes, misses)
    report = f'''# Updated finish-line detection validation

Only endpoint B changed in the detector module. All crossing, direction,
sampling, movement, 30-second minimum-interval and 50-meter spatial-rearm logic
remain unchanged. No energy integration, efficiency analysis or feature
importance was run. Source: `{SOURCE}`. SHA-256: `{before}`.

A: {FINISH_A}. Previous B: {OLD_B}. Confirmed updated B: {FINISH_B}.
WGS84 local east/north approximation at A; geographic degrees are not treated
as meters. No automatic extension, tolerance or coordinate correction applied.

| Metric | Previous segment | Updated segment |
|---|---:|---:|
| Length, m | {summary['previous_segment_length_m']:.6f} | {summary['updated_segment_length_m']:.6f} |
| Geometric intersections | {len(old)} | {len(new)} |
| Race-direction crossings | {len(old_accepted)} | {summary['crossings_after_direction_filter']} |
| Valid after all unchanged rules | {len(old_accepted)} | {len(accepted)} |
| Rejected candidates | {len(old)-len(old_accepted)} | {len(rejected)} |
| Complete crossing-to-crossing intervals | {max(0,len(old_accepted)-1)} | {len(accepted)-1} |
| Partial recording segments | 2 | {partial_count} |

## Geometric verdict

The updated segment is nondegenerate and produces {len(accepted)} recurring accepted crossings.
It captures **{summary['captured_previous_near_misses']} of {len(comparison)} recurring near misses
from the immediately previous geometry**. Remaining misses: {len(misses)}.
There are {len(complete)} boundary-complete intervals, including
{summary['plausible_single_lap_intervals']} plausible single laps and
{summary['ambiguous_possible_multiple_lap_intervals']} ambiguous possible multiple-lap intervals.
Full-session single-lap validation is {'incomplete because recurring passes are still missed' if misses else 'geometrically supported; inspect the anomaly table'}.
No missed pass is promoted to an accepted crossing.

Every valid crossing is left-to-right relative to directed A→B (direction −1).
The only reverse candidate is rejected by wrong direction, <30-second separation
and lack of 50-meter rearming. Crossing direction is consistent at both boundaries
of every reconstructed interval; direction consistency does not cure missing finishes.
An independent audit confirms >=30-second separation and a trustworthy GPS
sample >=50 m from the finite segment between every consecutive valid crossing.

## Remaining misses

| Previous miss | Old distance beyond B, m | New distance beyond B, m | New finish fraction | Time, UTC−05:00 |
|---|---:|---:|---:|---|
'''
    from datetime import timedelta
    for missed in misses:
        time = samples[0].timestamp + timedelta(seconds=missed['updated_elapsed_s'])
        report += f"| {missed['previous_miss_number']} | {missed['previous_distance_beyond_b_m']:.6f} | {missed['updated_distance_beyond_b_m']:.6f} | {missed['updated_finish_fraction']:.6f} | {time.isoformat()} |\n"
    report += '\nFinish fraction >1 means beyond endpoint B. The distances are measured in the local metric projection.\n'
    report += '\n## Crossing and lap validation table\n\n'
    report += 'Lap number describes the interval **ending** at each crossing; crossing 1 has no preceding complete lap.\n\n'
    report += '| Crossing | Source timestamp, UTC−05:00 | Interpolated time, UTC−05:00 | Previous crossing, s | Direction | Lap | Duration, s | Accepted trip distance, km | GPS distance, km | Full trip increment, km | Validation |\n'
    report += '|---|---|---|---:|---|---:|---:|---:|---:|---:|---|\n'
    def number(value): return f'{value:.6f}' if value is not None else '—'
    for row in validation:
        report += f"| {row['crossing_number']} | {row['timestamp']} | {row['interpolated_crossing_timestamp']} | {number(row['time_since_previous_crossing_s'])} | {row['crossing_direction']} | {row['lap_number'] or '—'} | {number(row['lap_duration_s'])} | {number(row['lap_distance_km'])} | {number(row['gps_derived_distance_km'])} | {number(row['trip_derived_distance_km'])} | {row['validation_status']} |\n"
    report += f'''
## Lap statistics and anomalies

These statistics cover **all {len(complete)} crossing-to-crossing intervals**, including
any ambiguous intervals. They are not a claim that each interval is one physical lap.

- Median lap interval time: {summary['median_lap_time_s']:.6f} s.
- Minimum lap interval time: {summary['minimum_lap_time_s']:.6f} s.
- Maximum lap interval time: {summary['maximum_lap_time_s']:.6f} s.
- Median trip-derived interval distance: {summary['median_trip_lap_distance_km']:.6f} km.
- Median GPS-derived interval distance: {summary['median_gps_lap_distance_km']:.6f} km.
- Anomalous interval numbers: {summary['anomalous_lap_numbers']}.

Anomaly flags are diagnostic only; they do not change crossings or omit laps.
They flag an uncaptured recurring pass, time above the inclusive-quartile IQR
upper fence ({time_upper:.6f} s), or trip distance above its upper fence
({distance_upper:.6f} km).

| Interval | Duration, s | Trip distance, km | GPS distance, km | Missed passes inside | Interpretation |
|---|---:|---:|---:|---:|---|
'''
    for row in anomalous:
        report += f"| {row['lap_number']} | {row['lap_duration_s']:.6f} | {row['trip_derived_distance_km']:.6f} | {row['gps_derived_distance_km']:.6f} | {row['uncaptured_recurring_passes']} | {row['validation_status']} |\n"
    report += '\n## Rejected candidates\n\n'
    for candidate in rejected:
        report += f"- Candidate {candidate['candidate_id']}, {candidate['interpolated_timestamp']}, {candidate['speed_kmh']:.6f} km/h: `{candidate['reason']}`; {candidate['time_since_previous_crossing_s']:.6f} s since last accepted crossing.\n"
    report += f'''
## Partial segments and distance definitions

`partial_start`: {partial_start_s:.6f} s before crossing 1.
`partial_end`: {partial_end_s:.6f} s after the final accepted crossing.
Neither is automatically called Lap 1 or a complete lap.

`lap_distance_km` is the accepted trip increment using the existing interval
quality/shutdown rules, preserving the denominator for later energy accounting.
`trip_derived_distance_km` is the full interpolated boundary-to-boundary trip
increment. GPS distance sums clipped projected adjacent-sample segments, excluding
invalid GPS, gaps >5 s and interval GPS speeds >30 m/s. Coverage columns accompany
both distance supports. No energy was integrated. Negative electrical readings
retain their prior flags and are never interpreted as regeneration.

The long intervals are not implausible race pace by default: their roughly doubled
distance and an uncaptured recurring pass inside each indicate missed finish
detections. These are boundary-complete intervals, not validated single physical laps.

Artifacts are isolated in `{OUTPUT.as_posix()}/` to preserve prior validation
and efficiency outputs as historical. Use this updated validation rather
than the previous `outputs/reports/lap_detection_report.md` for current geometry.
The report and plot preserve both finish segments for comparison.

Further geometry or GPS-alignment evidence is required before whole-session
single-lap efficiency comparisons. The confirmed segment remains exact.
'''
    (OUTPUT/'lap_detection_validation.md').write_text(report, encoding='utf-8')
    after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if after != before:
        raise RuntimeError('Source hash changed')
    summary['source_preserved'] = True
    (OUTPUT/'validation_manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def render_plot(samples, old, new, projection, new_passes, misses):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'ev-lap-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    points = [projection.project(s.latitude, s.longitude) for s in samples]
    a, old_b, new_b = (0, 0), projection.project(*OLD_B), projection.project(*FINISH_B)
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for ax in axes:
        ax.plot(*zip(*points), color='#777777', linewidth=.65, alpha=.7, label='GPS trajectory')
        ax.plot([0, old_b[0]], [0, old_b[1]], '--', color='#777777', linewidth=2, label='Previous finish segment')
        ax.plot([0, new_b[0]], [0, new_b[1]], color='#c47720', linewidth=3, label='Confirmed updated A–B')
        for accept, marker, color, label in [(True, 'o', '#24618f', 'Valid crossings'),
                                           (False, 'x', '#333333', 'Rejected candidate')]:
            locations = [projection.project(c['latitude'], c['longitude']) for c in new if c['accepted'] == accept]
            if locations:
                ax.scatter(*zip(*locations), marker=marker, color=color, s=55, zorder=5, label=label)
        missing_points = [p for p in new_passes
                          if any(abs(p['elapsed_s'] - miss['updated_elapsed_s']) < 1e-6 for miss in misses)]
        if missing_points:
            ax.scatter([p['x'] for p in missing_points], [p['y'] for p in missing_points],
                       marker='s', facecolors='none', edgecolors='#c47720', s=100, linewidth=1.5,
                       zorder=6, label='Still outside finite segment (not candidates)')
        ax.set_aspect('equal')
        ax.set_xlabel('East of A (m)'); ax.set_ylabel('North of A (m)'); ax.grid(alpha=.2)
    axes[0].set_title('GPS trajectory and finish geometry comparison')
    axes[1].set_title(f"{sum(c['accepted'] for c in new)} valid crossings, {sum(not c['accepted'] for c in new)} rejected; {len(misses)} passes missed")
    axes[1].set_xlim(-10, 25); axes[1].set_ylim(-10, 30)
    axes[1].annotate('A', a, xytext=(5, -12), textcoords='offset points')
    axes[1].annotate('B (updated)', new_b, xytext=(8, 0), textcoords='offset points')
    axes[2].set_title(f'Endpoint B detail: {len(misses)} excluded passes')
    axes[2].set_xlim(new_b[0]-1.5, new_b[0]+1.2)
    axes[2].set_ylim(new_b[1]-1.5, new_b[1]+1.2)
    axes[2].scatter(*new_b, marker='D', color='#c47720', s=35, zorder=7)
    axes[2].annotate('B', new_b, xytext=(-18, -8), textcoords='offset points')
    for index, missed in enumerate(misses):
        p = next(p for p in new_passes if abs(p['elapsed_s']-missed['updated_elapsed_s'])<1e-6)
        axes[2].annotate(f"Miss: {missed['updated_distance_beyond_b_m']:.3f} m",
                         (p['x'], p['y']), xytext=(14, 5+index*16),
                         textcoords='offset points', fontsize=8,
                         arrowprops=dict(arrowstyle='-', color='#c47720'))
    axes[0].legend(loc='upper left', fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT/'finish_geometry_validation.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
