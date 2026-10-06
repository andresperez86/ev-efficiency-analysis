"""Energy/pace comparison with inherited geometric ambiguity explicitly retained."""
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
VALIDATION = Path('outputs/lap_validation_revision2')
OUTPUT = Path('outputs/lap_energy_revision2')


def pareto_ids(frame):
    result = []
    for row in frame.to_dict('records'):
        dominated = any(
            other['wh_per_km'] <= row['wh_per_km']
            and other['lap_duration_s'] <= row['lap_duration_s']
            and (other['wh_per_km'] < row['wh_per_km']
                 or other['lap_duration_s'] < row['lap_duration_s'])
            for other in frame.to_dict('records'))
        if not dominated:
            result.append(int(row['lap_id']))
    return result


def correlations(frame):
    return dict(n=len(frame), pearson=float(frame['lap_duration_s'].corr(frame['wh_per_km'], method='pearson')),
                spearman=float(frame['lap_duration_s'].corr(frame['wh_per_km'], method='spearman')))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    manifest = json.loads((VALIDATION/'validation_manifest.json').read_text(encoding='utf-8'))
    if (manifest['source_sha256'] != source_hash or tuple(manifest['finish_a']) != FINISH_A
            or tuple(manifest['confirmed_finish_b']) != FINISH_B):
        raise ValueError('Source or finish geometry differs from the validated candidate boundaries')
    samples = load_csv(SOURCE)
    config = Config()
    crossings = detect_crossings(samples, expected_direction=-1)
    accepted = [c for c in crossings if c['accepted']]
    validation = pd.read_csv(VALIDATION/'crossing_lap_validation.csv')
    if len(accepted) != len(validation):
        raise ValueError('Crossing count differs from validation')
    for crossing, recorded in zip(accepted, validation.to_dict('records')):
        if crossing['interpolated_timestamp'] != recorded['interpolated_crossing_timestamp']:
            raise ValueError('Crossing timestamps differ from validation')
    rows = summarize_laps(samples, crossings, config, FINISH_A)
    ambiguous = set(manifest['anomalous_lap_numbers'])
    for row in rows:
        row['lap_validation_status'] = ('ambiguous_possible_multiple_physical_laps'
                                        if row['lap_id'] in ambiguous else 'plausible_single_lap')
        row['comparison_eligible'] = row['lap_id'] not in ambiguous and row['model_eligible']
        if row['shutdown_samples']:
            raise ValueError('Complete interval unexpectedly contains shutdown samples')
    frame = pd.DataFrame(rows).sort_values('lap_id')
    single = frame[frame['comparison_eligible']].copy()
    frontier = pareto_ids(single)
    frontier_all = pareto_ids(frame)
    frame['pareto_efficient_single_lap_comparison'] = frame['lap_id'].isin(frontier)
    frame['pareto_efficient_all_intervals'] = frame['lap_id'].isin(frontier_all)
    single = frame[frame['comparison_eligible']].copy()
    frame.to_csv(OUTPUT/'lap_summary.csv', index=False)
    columns = ['lap_id','start_timestamp','end_timestamp','lap_duration_s','lap_distance_km',
               'consumed_wh','wh_per_km','average_speed_kmh','max_speed_kmh',
               'average_power_w','peak_power_w','lap_validation_status',
               'coverage_fraction','pareto_efficient_single_lap_comparison','pareto_efficient_all_intervals']
    frame[columns].to_csv(OUTPUT/'lap_comparison.csv', index=False)
    for population, prefix in [(single,''),(frame,'all_intervals_')]:
        for filename, field in [('ranking_lowest_wh_per_km.csv','wh_per_km'),
                                ('ranking_fastest_lap.csv','lap_duration_s')]:
            ranking = population.sort_values([field,'lap_id'])[columns].copy()
            ranking.insert(0,'rank',range(1,len(ranking)+1))
            ranking.to_csv(OUTPUT/(prefix+filename),index=False)
    all_correlation = correlations(frame)
    single_correlation = correlations(single)
    summary = dict(source=str(SOURCE),source_sha256=source_hash,finish_a=FINISH_A,finish_b=FINISH_B,
                   complete_crossing_to_crossing_intervals=len(frame),plausible_single_laps=len(single),
                   ambiguous_intervals=sorted(ambiguous),partial_segments_excluded=2,
                   correlation_all_intervals=all_correlation,
                   correlation_excluding_ambiguous=single_correlation,
                   pareto_single_laps=frontier,pareto_all_intervals=frontier_all,
                   energy_policy='validated intervals; clip original endpoint power at zero; trapezoids over actual dt; matched trip support',
                   fastest_lap=int(single.loc[single['lap_duration_s'].idxmin(),'lap_id']),
                   most_efficient_lap=int(single.loc[single['wh_per_km'].idxmin(),'lap_id']),
                   importance_modeling_run=False)
    # Conservation check over exactly the same first-to-last crossing support.
    intervals = make_intervals(samples,flag_samples(samples,config),config)
    support = [p for i in intervals
               if (p := clip_interval(i,accepted[0]['elapsed_s'],accepted[-1]['elapsed_s'])) is not None]
    total = account(support, [])
    for column,key in [('consumed_wh','consumed_wh'),('lap_distance_km','distance_km')]:
        if abs(frame[column].sum()-total[key]) > 1e-8:
            raise ValueError(f'Boundary partition failed for {column}')
    if not ((frame['consumed_wh'] >= 0).all() and
            ((frame['wh_per_km']-frame['consumed_wh']/frame['lap_distance_km']).abs()<1e-10).all()):
        raise ValueError('Invalid energy or Wh/km')
    summary['complete_interval_consumed_wh'] = float(frame['consumed_wh'].sum())
    summary['energy_distance_partition_verified'] = True
    render(frame,frontier)
    report = '''# Lap energy and pace comparison

The supplied exact finish geometry defines ten crossing-to-crossing intervals.
Intervals 4 and 9 still contain missed finishes and may each span multiple
physical laps. Their metrics are retained, explicitly marked, and excluded from
the primary single-lap rankings. All-interval rankings and correlations are also
exported as a sensitivity comparison. Original lap IDs are preserved.

Energy uses the established electrically validated support, excludes shutdown
and post-run intervals, clips **original endpoint** power at zero, and integrates
piecewise-linearly with actual timestamp spacing. Interpolated crossing boundaries
partition original intervals without duplication. Wh/km uses trip increments
over exactly the same accepted support; partial recording segments are excluded.
Negative current/power are flagged artifacts, never recovered energy. No source
CSV changes and no feature-importance modeling were performed.

Average speed and discharge power are duration-weighted over accepted intervals;
maximum speed and peak power include interpolated endpoints. Local timestamps
are UTC−05:00 on 2025-11-07. All ten intervals have full accepted-time coverage.

| Lap/interval | Start | End | Duration s | Distance km | Consumed Wh | Wh/km | Avg speed km/h | Max speed km/h | Avg discharge W | Peak discharge W | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
'''
    for row in frame.to_dict('records'):
        start = row['start_timestamp'].split('T')[1]
        end = row['end_timestamp'].split('T')[1]
        report += (f"| {row['lap_id']} | {start} | {end} | {row['lap_duration_s']:.3f} | "
                   f"{row['lap_distance_km']:.6f} | {row['consumed_wh']:.6f} | {row['wh_per_km']:.6f} | "
                   f"{row['average_speed_kmh']:.3f} | {row['max_speed_kmh']:.3f} | "
                   f"{row['average_power_w']:.3f} | {row['peak_power_w']:.3f} | {row['lap_validation_status']} |\n")
    report += '\n## Rankings\n\n'
    for name,field in [('Lowest Wh/km','wh_per_km'),('Fastest time','lap_duration_s')]:
        report += f"{name}, plausible single laps: {single.sort_values([field,'lap_id'])['lap_id'].tolist()}.\n\n"
        report += f"{name}, all intervals (4/9 ambiguous): {frame.sort_values([field,'lap_id'])['lap_id'].tolist()}.\n\n"
    report += f'''
## Correlation and tradeoff

| Population | n | Pearson (time vs Wh/km) | Spearman (time vs Wh/km) |
|---|---:|---:|---:|
| Plausible single laps, excluding 4/9 | {len(single)} | {single_correlation['pearson']:.6f} | {single_correlation['spearman']:.6f} |
| All boundary-complete intervals | {len(frame)} | {all_correlation['pearson']:.6f} | {all_correlation['spearman']:.6f} |

These are descriptive associations, not causal effects. Small single-session
samples, course/operating state, unequal interval lengths and the Wh/km ratio
limit interpretation. No strategy recommendation follows from correlation alone.

Pareto-efficient plausible single laps: **{frontier}**, jointly minimizing
lap time and Wh/km. All-interval Pareto set: {frontier_all}.
Fastest plausible lap: {summary['fastest_lap']}. Lowest Wh/km plausible lap:
{summary['most_efficient_lap']}. The frontier offers observed tradeoffs; it does
not establish an optimal racing strategy without an acceptable race-pace floor.

The source SHA-256 remains `{source_hash}`. Summed interval energy and distance
were verified against the first-to-last-crossing accounting support. The manifest
preserves the unresolved ambiguity; this analysis does not declare intervals
4/9 validated physical laps.

Files: `lap_comparison.csv`, `lap_summary.csv`, `ranking_lowest_wh_per_km.csv`,
`ranking_fastest_lap.csv`, their `all_intervals_` counterparts,
`efficiency_vs_lap_time.png`, and `energy_comparison_manifest.json`.
'''
    indexed = frame.set_index('lap_id')
    extra_s = indexed.loc[5,'lap_duration_s'] - indexed.loc[1,'lap_duration_s']
    saving_pct = 100*(1-indexed.loc[5,'wh_per_km']/indexed.loc[1,'wh_per_km'])
    report += f'''
## Practical comparison

Lap 1 is fastest ({indexed.loc[1,'lap_duration_s']:.3f} s), but has the highest
Wh/km among plausible single laps ({indexed.loc[1,'wh_per_km']:.6f} Wh/km).
It remains Pareto efficient because no other lap is faster.
Lap 8 has the lowest Wh/km ({indexed.loc[8,'wh_per_km']:.6f}), at
{indexed.loc[8,'lap_duration_s']:.3f} s and {indexed.loc[8,'consumed_wh']:.6f} Wh.
Lap 5 is a useful near-fastest tradeoff: only {extra_s:.6f} s slower than lap 1,
with {saving_pct:.3f}% lower Wh/km. Lap 6 is dominated by lap 5, which is both
faster and lower in Wh/km. Laps 7, 10 and 3 give intermediate observed tradeoffs,
while 2 and 8 occupy the slower, lower-consumption end. These observations do
not establish that changing driving behavior causes the observed differences.
'''
    (OUTPUT/'lap_energy_report.md').write_text(report,encoding='utf-8')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError('Source hash changed')
    summary['source_preserved'] = True
    (OUTPUT/'energy_comparison_manifest.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(frame[columns].to_string(index=False))
    print(json.dumps(summary,indent=2))


def render(frame,frontier):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'ev-lap-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax = plt.subplots(figsize=(10,6))
    for ids,marker,color,label in [(frame[frame['comparison_eligible']]['lap_id'].tolist(),'o','#24618f','Plausible single laps'),
                                   (frame[~frame['comparison_eligible']]['lap_id'].tolist(),'s','#777777','Ambiguous intervals: possible multiple laps')]:
        subset = frame[frame['lap_id'].isin(ids)]
        ax.scatter(subset['lap_duration_s'],subset['wh_per_km'],marker=marker,color=color,s=65,label=label)
    selected = frame[frame['lap_id'].isin(frontier)].sort_values('lap_duration_s')
    ax.plot(selected['lap_duration_s'],selected['wh_per_km'],color='#c47720',linestyle='--',lw=1.2)
    ax.scatter(selected['lap_duration_s'],selected['wh_per_km'],marker='*',color='#c47720',
               edgecolors='#333333',linewidth=.5,s=190,zorder=5,label='Pareto frontier among plausible single laps')
    for row in frame.to_dict('records'):
        dx,dy = (7,7) if row['lap_id'] != 5 else (7,-16)
        ax.annotate(str(row['lap_id'])+('*' if not row['comparison_eligible'] else ''),
                    (row['lap_duration_s'],row['wh_per_km']),xytext=(dx,dy),textcoords='offset points')
    ax.set_xlabel('Lap / crossing-to-crossing interval time (s)')
    ax.set_ylabel('Consumed energy per distance (Wh/km)')
    ax.set_title('Energy versus pace: exact finish geometry')
    ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.text(.12,.015,'* Intervals 4 and 9 remain geometrically ambiguous; association is not causation.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(OUTPUT/'efficiency_vs_lap_time.png',dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
