"""Validate measured lap lengths before ranking measured km/Wh; no assumed lap count."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from ev_analysis.contracts import Config
from ev_analysis.ingestion import load_csv
from ev_analysis.laps import FINISH_A, FINISH_B, detect_crossings, summarize_laps
from ev_analysis.metrics import account, clip_interval, make_intervals
from ev_analysis.quality import flag_samples

SOURCE = Path('C:/Users/ANDRÉS PÉREZ/Projects/ResultadosGP_limpios/datos_limpios/EIA_clean.csv')
OUTPUT = Path('outputs/lap_km_per_wh')
EXPECTED_KM = 1.21
DISTANCE_TOLERANCE_PCT = 10.0  # Explicit exploratory policy for "approximately".


def pareto(frame):
    records = frame.to_dict('records')
    return [int(row['lap']) for row in records if not any(
        other['lap_time_s'] <= row['lap_time_s'] and other['km_per_Wh'] >= row['km_per_Wh']
        and (other['lap_time_s'] < row['lap_time_s'] or other['km_per_Wh'] > row['km_per_Wh'])
        for other in records)]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    original_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    samples = load_csv(SOURCE)
    config = Config()
    crossings = detect_crossings(samples, expected_direction=-1)
    accepted = [crossing for crossing in crossings if crossing['accepted']]
    intervals = make_intervals(samples, flag_samples(samples, config), config)
    # No fixed number of laps, invalid lap IDs, or historical anomaly list is used.
    rows = summarize_laps(samples, crossings, config, FINISH_A)
    full = pd.DataFrame(rows).sort_values('lap_id')
    full['trip_deviation_pct'] = 100*(full['trip_distance_km']/EXPECTED_KM-1)
    full['gps_deviation_pct'] = 100*(full['gps_distance_km']/EXPECTED_KM-1)
    full['distance_consistent'] = ((full['trip_deviation_pct'].abs() <= DISTANCE_TOLERANCE_PCT)
                                   & (full['gps_deviation_pct'].abs() <= DISTANCE_TOLERANCE_PCT))
    full['validated_single_lap'] = (full['distance_consistent'] & full['model_eligible']
                                  & (full['gps_coverage_fraction'] >= config.minimum_window_coverage)
                                  & (full['shutdown_samples'] == 0))
    full['validation_status'] = full['validated_single_lap'].map({True:'validated_single_lap',False:'invalid_or_unresolved_interval'})
    full.to_csv(OUTPUT/'all_crossing_intervals.csv', index=False)
    validation_columns = ['lap_id','start_timestamp','end_timestamp','lap_duration_s','trip_distance_km',
                          'gps_distance_km','trip_deviation_pct','gps_deviation_pct','validation_status']
    full[validation_columns].to_csv(OUTPUT/'lap_distance_validation.csv',index=False)
    valid = full[full['validated_single_lap']].copy()
    valid['km_per_Wh'] = valid['lap_distance_km']/valid['consumed_wh'].replace(0,float('nan'))
    valid['Wh_per_km'] = valid['consumed_wh']/valid['lap_distance_km']
    if not valid[['km_per_Wh','Wh_per_km']].notna().all().all():
        raise ValueError('Zero energy/distance prevents finite reciprocal efficiency comparison')
    aliases = dict(lap_id='lap',lap_duration_s='lap_time_s',
                   consumed_wh='energy_Wh',average_speed_kmh='avg_speed_kmh',max_speed_kmh='max_speed_kmh',
                   average_power_w='avg_discharge_power_W',peak_power_w='peak_power_W',
                   average_current_a='avg_current_A',peak_current_a='peak_current_A')
    valid = valid.rename(columns=aliases)
    frontier = pareto(valid)
    valid['pareto_efficient'] = valid['lap'].isin(frontier)
    primary_columns = ['lap','lap_time_s','distance_km','energy_Wh','km_per_Wh','Wh_per_km','avg_speed_kmh','peak_power_W']
    detail_columns = primary_columns+['start_timestamp','end_timestamp','max_speed_kmh','avg_discharge_power_W',
                                     'avg_current_A','peak_current_A','pareto_efficient','trip_deviation_pct','gps_deviation_pct']
    valid[primary_columns].to_csv(OUTPUT/'lap_comparison.csv',index=False)
    valid[detail_columns].to_csv(OUTPUT/'lap_metrics.csv',index=False)
    ranking_spec = [('highest_km_per_Wh','km_per_Wh',False),('fastest_lap','lap_time_s',True),
                    ('lowest_Wh_per_km','Wh_per_km',True),('lowest_energy_Wh','energy_Wh',True)]
    rankings = {}
    for name,field,ascending in ranking_spec:
        ranked = valid.sort_values([field,'lap'],ascending=[ascending,True])[detail_columns].copy()
        ranked.insert(0,'rank',range(1,len(ranked)+1))
        ranked.to_csv(OUTPUT/f'ranking_{name}.csv',index=False)
        rankings[name] = ranked['lap'].tolist()
    partials = []
    boundaries = [('partial_start',0,accepted[0]['elapsed_s'],samples[0].timestamp.isoformat(),accepted[0]['interpolated_timestamp']),
                  ('partial_end',accepted[-1]['elapsed_s'],(samples[-1].timestamp-samples[0].timestamp).total_seconds(),
                   accepted[-1]['interpolated_timestamp'],samples[-1].timestamp.isoformat())]
    for status,lo,hi,start,end in boundaries:
        support = [p for interval in intervals if (p:=clip_interval(interval,lo,hi)) is not None]
        metrics = account(support, [])
        partials.append(dict(lap_status=status,start_timestamp=start,end_timestamp=end,duration_s=hi-lo,
                             accepted_trip_distance_km=metrics['distance_km'],accepted_duration_s=metrics['valid_duration_s'],
                             excluded_duration_s=hi-lo-metrics['valid_duration_s'],included_in_ranking=False))
    pd.DataFrame(partials).to_csv(OUTPUT/'partial_laps.csv',index=False)
    summary = dict(source=str(SOURCE),source_sha256=original_hash,finish_a=FINISH_A,finish_b=FINISH_B,
                   expected_lap_distance_km=EXPECTED_KM,distance_tolerance_pct=DISTANCE_TOLERANCE_PCT,
                   predefined_lap_count=None,geometric_crossings=len(crossings),valid_crossings=len(accepted),
                   complete_crossing_intervals=len(full),validated_single_laps=len(valid),
                   valid_interval_ids=valid['lap'].tolist(),
                   distance_inconsistent_interval_ids=full.loc[~full['distance_consistent'],'lap_id'].tolist(),
                   partial_segments=len(partials),total_physical_race_lap_count='unresolved_due_to_missing_finish_crossings',
                   mean_lap_distance_km=float(valid['distance_km'].mean()),
                   median_lap_distance_km=float(valid['distance_km'].median()),
                   mean_gps_distance_km=float(full.loc[full['validated_single_lap'],'gps_distance_km'].mean()),
                   median_gps_distance_km=float(full.loc[full['validated_single_lap'],'gps_distance_km'].median()),
                   pearson_lap_time_vs_km_per_Wh=float(valid['lap_time_s'].corr(valid['km_per_Wh'],method='pearson')),
                   spearman_lap_time_vs_km_per_Wh=float(valid['lap_time_s'].corr(valid['km_per_Wh'],method='spearman')),
                   fastest_lap=rankings['fastest_lap'][0],most_efficient_lap=rankings['highest_km_per_Wh'][0],
                   least_efficient_lap=rankings['highest_km_per_Wh'][-1],pareto_laps=frontier,rankings=rankings,
                   trip_distance_valid_ids_at_5pct=full.loc[full['trip_deviation_pct'].abs()<=5,'lap_id'].tolist(),
                   importance_modeling_run=False)
    indexed = valid.set_index('lap')
    fast_id = summary['fastest_lap']
    # Report the closest-in-time alternative to the fastest point on the Pareto frontier.
    alternatives = valid[(valid['lap'] != fast_id) & valid['pareto_efficient']]
    compromise = alternatives.sort_values(['lap_time_s','lap']).iloc[0]
    summary['near_fastest_compromise_lap'] = int(compromise['lap'])
    summary['compromise_extra_time_s'] = float(compromise['lap_time_s']-indexed.loc[fast_id,'lap_time_s'])
    summary['compromise_km_per_Wh_improvement_pct'] = float(100*(compromise['km_per_Wh']/indexed.loc[fast_id,'km_per_Wh']-1))
    summary['compromise_Wh_per_km_reduction_pct'] = float(100*(1-compromise['Wh_per_km']/indexed.loc[fast_id,'Wh_per_km']))
    if not ((valid['km_per_Wh']*valid['Wh_per_km']-1).abs()<1e-12).all():
        raise ValueError('Reciprocal efficiency identity failed')
    for row in valid.to_dict('records'):
        lo,hi = next((a['elapsed_s'],b['elapsed_s']) for i,(a,b) in enumerate(zip(accepted,accepted[1:]),1) if i==row['lap'])
        support = [p for interval in intervals if (p:=clip_interval(interval,lo,hi)) is not None]
        measured = account(support, [])
        if abs(measured['consumed_wh']-row['energy_Wh'])>1e-9 or abs(measured['distance_km']-row['distance_km'])>1e-9:
            raise ValueError('Validated-lap accounting support mismatch')
    render(valid,frontier)
    report = f'''# Distance-validated lap efficiency in km/Wh

## Count and validation first

No race lap count is assumed. The exact finite finish line produces {len(crossings)}
geometric candidates and {len(accepted)} valid same-direction crossings, delimiting
{len(full)} complete crossing-to-crossing intervals. Of these, {len(valid)} satisfy
the single-lap distance/coverage criteria; {len(full)-len(valid)} are invalid or unresolved
single-lap intervals. The full physical race lap count is unresolved because
the finite line still misses two recurring passes. No virtual finish, automatic
line extension, splitting into assumed laps or renumbering has been applied.

Expected distance is approximately {EXPECTED_KM} km, not a replacement for measured
distance. An explicit exploratory ±{DISTANCE_TOLERANCE_PCT}% consistency screen is used
for both trip and GPS estimates (not a confirmed engineering tolerance). Trip distance
is the primary accounting distance. Tightening the trip screen to ±5% gives the
same IDs: {summary['trip_distance_valid_ids_at_5pct']}. The retained trip estimates
are all within roughly 1.3% of 1.21 km; GPS chord distances are systematically
lower and are independently displayed. Coverage must be >=90%, with no shutdown
samples in an eligible lap. Long/short distances are flagged, never corrected.

| Interval ID | Start timestamp | End timestamp | Time s | Trip km | GPS km | Trip deviation % | GPS deviation % | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
'''
    for row in full.to_dict('records'):
        report += f"| {row['lap_id']} | {row['start_timestamp']} | {row['end_timestamp']} | {row['lap_duration_s']:.3f} | {row['trip_distance_km']:.6f} | {row['gps_distance_km']:.6f} | {row['trip_deviation_pct']:+.3f} | {row['gps_deviation_pct']:+.3f} | {row['validation_status']} |\n"
    report += '\n## Partial recording segments (excluded)\n\n'
    for partial in partials:
        report += f"- `{partial['lap_status']}`: {partial['start_timestamp']} to {partial['end_timestamp']}, {partial['duration_s']:.3f} s; accepted trip {partial['accepted_trip_distance_km']:.6f} km, excluded duration {partial['excluded_duration_s']:.3f} s.\n"
    report += '''
Intervals 4 and 9 are approximately 2.43 km, around twice the expected distance,
and unusually long in time. They contain previously identified missing finishes:
they are not validated single laps and never enter any ranking, correlation
or Pareto analysis here. No distance-inconsistent short single-lap interval is found.
Original interval IDs are retained, so the valid IDs need not be contiguous.

## Validated single-lap comparison

km/Wh = measured accepted trip distance / consumed Wh (higher is better).
Wh/km = consumed Wh / the same measured distance (lower is better).
No regeneration: clip original endpoint power at zero on electrically validated
support, integrate trapezoids over actual elapsed time, and clip intervals at
interpolated crossing boundaries. Negative values remain flagged, never recovered
energy. Partial and shutdown/post-run intervals are excluded. No distance is forced
to 1.21 km. Current averages/peaks represent clipped discharge current; raw values
remain in the underlying telemetry. Speed and electrical averages are time weighted.

| Lap | Time s | Distance km | Energy Wh | km/Wh | Wh/km | Avg speed km/h | Peak power W |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
    for row in valid.to_dict('records'):
        report += f"| {row['lap']} | {row['lap_time_s']:.3f} | {row['distance_km']:.6f} | {row['energy_Wh']:.6f} | {row['km_per_Wh']:.6f} | {row['Wh_per_km']:.6f} | {row['avg_speed_kmh']:.3f} | {row['peak_power_W']:.3f} |\n"
    report += '\n`lap_metrics.csv` also contains start/end timestamps, maximum speed, average discharge power, average current and peak current.\n'
    report += '\n## Rankings (validated single laps only)\n\n'
    for name,ids in rankings.items(): report += f'- {name}: {ids}.\n'
    report += f'''
## Performance and efficiency

Mean measured trip lap distance: {summary['mean_lap_distance_km']:.6f} km.
Median measured trip lap distance: {summary['median_lap_distance_km']:.6f} km.
Mean/median GPS lap distance: {summary['mean_gps_distance_km']:.6f}/{summary['median_gps_distance_km']:.6f} km.
Pearson lap time vs km/Wh: {summary['pearson_lap_time_vs_km_per_Wh']:.6f}.
Spearman lap time vs km/Wh: {summary['spearman_lap_time_vs_km_per_Wh']:.6f}.
In these validated intervals, longer times tend to accompany higher km/Wh,
so faster laps tend to be less efficient. This is association, not causation;
small single-session samples and operating conditions limit interpretation.
Pearson must be recomputed for the reciprocal metric, not merely sign-flipped.

Pareto-efficient laps minimize time and maximize km/Wh: {frontier}.
Fastest lap: {summary['fastest_lap']}; most efficient: {summary['most_efficient_lap']};
least efficient: {summary['least_efficient_lap']}.
The closest-in-time Pareto alternative to the fastest lap is
lap {summary['near_fastest_compromise_lap']}: {summary['compromise_extra_time_s']:.6f} s slower,
{summary['compromise_km_per_Wh_improvement_pct']:.3f}% higher km/Wh and
{summary['compromise_Wh_per_km_reduction_pct']:.3f}% lower Wh/km.
This is a useful observed compromise, not a uniquely optimal strategy;
a team-selected pace/energy preference is needed to choose among Pareto points.

The scatter plot uses time on x and km/Wh on y: upper-left is fast/efficient,
lower-left fast/inefficient, upper-right efficient/slow, lower-right slow/inefficient.
No invalid/partial interval is plotted as a ranked lap.

Source SHA-256: `{original_hash}`. Detector, finish geometry and electrical
accounting rules are unchanged. No feature-importance model was run.
'''
    (OUTPUT/'lap_validation_efficiency_report.md').write_text(report,encoding='utf-8')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=original_hash:
        raise RuntimeError('Source hash changed')
    summary['source_preserved'] = True
    (OUTPUT/'manifest.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(full[validation_columns].to_string(index=False))
    print(valid[primary_columns].to_string(index=False))
    print(json.dumps(summary,indent=2))


def render(frame,frontier):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'ev-lap-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax = plt.subplots(figsize=(10,6))
    ax.scatter(frame['lap_time_s'],frame['km_per_Wh'],color='#24618f',s=65,label='Distance-validated single laps')
    selected = frame[frame['lap'].isin(frontier)].sort_values('lap_time_s')
    ax.plot(selected['lap_time_s'],selected['km_per_Wh'],'--',color='#c47720',lw=1.2)
    ax.scatter(selected['lap_time_s'],selected['km_per_Wh'],marker='*',s=190,color='#c47720',
               edgecolors='#333333',lw=.5,zorder=5,label='Pareto efficient: less time, more km/Wh')
    for row in frame.to_dict('records'):
        dx,dy = (7,7) if row['lap']!=5 else (7,-15)
        ax.annotate(str(row['lap']),(row['lap_time_s'],row['km_per_Wh']),xytext=(dx,dy),textcoords='offset points')
    ax.set_xlabel('Lap time (s) — faster ←')
    ax.set_ylabel('Efficiency (km/Wh) — more efficient ↑')
    ax.set_title('Measured single-lap energy efficiency versus performance')
    ax.grid(alpha=.2); ax.legend(loc='upper left',fontsize=8)
    fig.text(.12,.015,'Invalid intervals 4/9 and partial segments excluded; no predefined race lap count.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(OUTPUT/'efficiency_km_per_Wh_vs_lap_time.png',dpi=180)
    plt.close(fig)


if __name__=='__main__': main()
