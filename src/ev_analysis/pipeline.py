"""CLI orchestration of the auditable EDA pipeline."""

import argparse
import hashlib
import platform
from dataclasses import asdict, replace
from importlib import metadata
from math import isfinite
from pathlib import Path

from .contracts import Config
from .ingestion import load_csv, read_records, NUMERIC
from .quality import flag_samples, profile, numeric_summary
from .metrics import make_intervals, account
from .features import build_windows, EXPLANATORY_FEATURES
from .eda import relationship_table, compare_periods, pearson, spearman
from .modeling import model_importance
from .reporting import write_json, write_csv, dictionary, findings
from .figures import xy_plot, histogram, boxplot, correlation_matrix


def run(source: Path, output: Path, config: Config = Config()) -> dict:
    source = source.resolve()
    output = output.resolve()
    if source.is_relative_to(output):
        raise ValueError('Output directory cannot contain the source CSV')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    columns, records = read_records(source)
    samples = load_csv(source)
    flags = flag_samples(samples, config)
    quality = profile(samples, columns, records, flags)
    intervals = make_intervals(samples, flags, config)
    metrics = account(intervals, samples)
    windows = build_windows(intervals, samples, config)
    relationships = relationship_table(windows, config.seed)
    comparisons = compare_periods(windows)
    modeling = model_importance(windows, config.seed)
    figures, tables, reports = (output / name for name in ('figures', 'tables', 'reports'))
    for folder in (figures, tables, reports):
        folder.mkdir(parents=True, exist_ok=True)
    write_json(reports / 'quality.json', quality)
    write_json(reports / 'metrics.json', metrics)
    write_json(reports / 'comparisons.json', comparisons)
    write_json(reports / 'modeling.json', modeling)
    write_csv(tables / 'data_dictionary.csv', dictionary(quality))
    write_csv(tables / 'sample_quality_flags.csv', [
        {**r, 'source_csv_row': s.source_row, 'flags': '|'.join(sorted(f))}
        for r, s, f in zip(records, samples, flags)])
    write_csv(tables / 'interval_ledger.csv', [
        {'left_csv_row': i.left.source_row, 'right_csv_row': i.right.source_row,
         'start': i.left.timestamp.isoformat(), 'end': i.right.timestamp.isoformat(),
         'duration_s': i.duration_s, 'accepted': i.valid, 'exclusion_reasons': '|'.join(i.reasons),
         'left_flags': '|'.join(sorted(a)), 'right_flags': '|'.join(sorted(b)),
         'negative_power_clipped': i.left.power_w < 0 or i.right.power_w < 0,
         'trip_increment_km': i.right.trip_km-i.left.trip_km}
        for i, a, b in zip(intervals, flags, flags[1:])])
    write_csv(tables / 'operating_periods.csv', windows)
    write_csv(tables / 'candidate_associations.csv', relationships)
    mostly_moving = [w for w in windows if w['model_eligible'] and w['stopped_pct'] <= 5]
    moving_relationships = relationship_table(mostly_moving, config.seed)
    write_csv(tables / 'candidate_associations_mostly_moving.csv', moving_relationships)
    write_json(reports / 'mostly_moving_comparisons.json', compare_periods(mostly_moving))
    write_csv(tables / 'summary_statistics.csv', [{'variable': name, **stats} for name, stats in quality['numeric'].items()])
    eligible = [w for w in windows if w['model_eligible']]
    fields = ['wh_per_km', *EXPLANATORY_FEATURES]
    matrix_rows = []
    for a in fields:
        for b in fields:
            matrix_rows.append({'variable_a': a, 'variable_b': b, 'n': len(eligible),
                                'pearson': pearson([w[a] for w in eligible], [w[b] for w in eligible]),
                                'spearman': spearman([w[a] for w in eligible], [w[b] for w in eligible])})
    write_csv(tables / 'correlation_matrix.csv', matrix_rows)
    write_csv(tables / 'pace_matched_pairs.csv', comparisons.get('pace_matched_pairs_2kmh', []),
              ['efficient_period', 'inefficient_period', 'difference_wh_per_km', 'speed_difference_kmh'])
    if modeling['status'] == 'computed':
        write_csv(tables / 'predictive_importance.csv', modeling['importance'])
        write_csv(tables / 'validation_folds.csv', modeling['folds'])
    sensitivity = []
    for seconds in (30.0, 60.0, 120.0):
        period_config = replace(config, window_s=seconds)
        period_windows = build_windows(intervals, samples, period_config)
        assoc = relationship_table(period_windows, config.seed)
        write_csv(tables / f'associations_{int(seconds)}s.csv', assoc)
        write_csv(tables / f'periods_{int(seconds)}s.csv', period_windows)
        sensitivity.append({'window_s': seconds, 'eligible_periods': sum(w['model_eligible'] for w in period_windows),
                            'top_three_associations': [r['feature'] for r in assoc if r['association_score'] is not None][:3]})
    alternative = [replace(i, valid=False, reasons=tuple(sorted(set(i.reasons) | {'negative_artifact_sensitivity'})))
                   if i.left.power_w < 0 or i.right.power_w < 0 or i.left.current_a < 0 or i.right.current_a < 0 else i for i in intervals]
    write_json(reports / 'negative_artifact_sensitivity.json', account(alternative, samples))
    write_json(reports / 'window_sensitivity.json', sensitivity)
    write_json(reports / 'shutdown_threshold_sensitivity.json', [
        {'shutdown_voltage_v': threshold, **account(make_intervals(samples,
            flag_samples(samples, replace(config, shutdown_voltage_v=threshold)),
            replace(config, shutdown_voltage_v=threshold)), samples)}
        for threshold in (1.0, 10.0, 40.0)])
    active_elapsed = sum(max(i.duration_s, 0) for i, a, b in zip(intervals, flags, flags[1:])
                         if 'shutdown_post_run' not in a | b)
    write_json(reports / 'coverage.json', {'full_record': metrics['coverage_fraction'],
               'non_shutdown_interval_duration_s': active_elapsed,
               'valid_fraction_of_non_shutdown_intervals': metrics['valid_duration_s']/active_elapsed if active_elapsed else None})
    inventory = []
    for file in sorted(source.parent.glob('*.csv')):
        import csv
        with file.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
            count = sum(1 for _ in reader)
        inventory.append({'filename': file.name, 'rows': count, 'columns': '|'.join(header),
                          'lap_identifier_found': any('lap' in c.lower() or 'vuelta' in c.lower() for c in header)})
    write_csv(tables / 'related_dataset_inventory.csv', inventory)
    for column, field in NUMERIC.items():
        values = [getattr(s, field) for s in samples]
        unit = next(r['unit'] for r in dictionary(quality) if r['column'] == column)
        histogram(figures / f'histogram_{column}.svg', f'{column}: all recorded samples', values, unit)
        boxplot(figures / f'boxplot_{column}.svg', f'{column}: raw distribution', {'all samples': values}, unit)
        xy_plot(figures / f'timeseries_{column}.svg', f'{column}: raw telemetry; shutdown retained',
                [((s.timestamp-samples[0].timestamp).total_seconds(), getattr(s, field)) for s in samples],
                'Elapsed competition time (s)', unit, line=True)
    xy_plot(figures / 'gps_trace_provisional.svg', 'Provisional GPS track (coordinate order unconfirmed)',
            [(s.longitude, s.latitude) for s in samples], 'Likely longitude (degrees)', 'Likely latitude (degrees)', line=True)
    for field in EXPLANATORY_FEATURES:
        xy_plot(figures / f'efficiency_vs_{field}.svg', f'Wh/km versus {field}: operating periods',
                [(w[field], w['wh_per_km']) for w in eligible], field, 'Wh/km')
    pareto_ids = set(comparisons.get('pareto_periods', []))
    xy_plot(figures / 'efficiency_vs_pace.svg', 'Efficiency versus pace; orange = Pareto periods',
            [(w['average_speed_kmh'], w['wh_per_km']) for w in eligible], 'Average speed (km/h)', 'Wh/km',
            highlights={i for i, w in enumerate(eligible) if w['period_id'] in pareto_ids})
    xy_plot(figures / 'efficiency_over_time.svg', 'Period efficiency over competition time',
            [(w['start_s'], w['wh_per_km']) for w in eligible], 'Elapsed time (s)', 'Wh/km')
    histogram(figures / 'histogram_wh_per_km.svg', 'Eligible-period efficiency', [w['wh_per_km'] for w in eligible], 'Wh/km')
    sorted_periods = sorted(eligible, key=lambda w: w['wh_per_km'])
    n = max(1, len(sorted_periods)//4)
    boxplot(figures / 'efficient_inefficient_pace.svg', 'Pace by efficiency quartile',
            {'efficient': [w['average_speed_kmh'] for w in sorted_periods[:n]],
             'inefficient': [w['average_speed_kmh'] for w in sorted_periods[-n:]]}, 'km/h')
    correlation_matrix(figures / 'correlation_matrix.svg', eligible,
                       ['wh_per_km', 'average_speed_kmh', 'speed_std_kmh', 'stopped_pct',
                        'acceleration_pct', 'deceleration_pct', 'speed_40_plus_pct'])
    packages = {}
    for name in ('numpy', 'scikit-learn', 'shap', 'pytest', 'pytest-cov'):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    write_json(reports / 'manifest.json', {'source': str(source), 'source_sha256': source_hash,
               'config': asdict(config), 'python': platform.python_version(), 'packages': packages,
               'analysis_version': '0.1.0', 'source_preserved': source_hash == hashlib.sha256(source.read_bytes()).hexdigest(),
               'modeling_status': modeling['status'], 'lap_reconstruction': 'not_implemented_pending_GPS_and_finish_line_confirmation',
               'figure_backend': 'deterministic SVG; matplotlib unavailable',
               'units': {'speed': 'km/h', 'trip': 'km', 'power': 'W', 'voltage': 'V', 'current': 'A', 'time': 'UTC-05:00'}})
    report_text = findings(quality, metrics, comparisons, relationships, modeling, sensitivity)
    report_text += ('\n## Mostly-moving sensitivity\n\n'
                   'This optional descriptive subset accepts periods with at most 5% stopped time; it is not a confirmed competitive pace floor.\n\n'
                   f'Eligible periods: {len(mostly_moving)}. Leading associations: '
                   + ', '.join('{} (Pearson={}, Spearman={})'.format(r['feature'], r['pearson'], r['spearman']) for r in moving_relationships[:5])
                   + '.\n\nThe lowest raw period Wh/km can occur in terminal coasting. Inspect pace and operating state before interpreting efficiency rankings. Window-size sensitivity shows whether candidate ordering is stable.\n')
    moving_comparisons = compare_periods(mostly_moving)
    if moving_comparisons.get('eligible_count'):
        report_text += ('\nMostly-moving efficient quartile medians: '
                        + str(moving_comparisons['efficient_quartile_medians'])
                        + '. Inefficient quartile medians: '
                        + str(moving_comparisons['inefficient_quartile_medians'])
                        + '. Lower consumption in these groups can accompany lower pace; the trade-off needs matched-lap validation.\n')
    (reports / 'findings.md').write_text(report_text, encoding='utf-8')
    if source_hash != hashlib.sha256(source.read_bytes()).hexdigest():
        raise RuntimeError('Source changed during analysis')
    return {'quality': quality, 'metrics': metrics, 'relationships': relationships,
            'comparisons': comparisons, 'modeling': modeling}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs'))
    parser.add_argument('--window-s', type=float, default=60)
    parser.add_argument('--max-gap-s', type=float, default=5)
    parser.add_argument('--moving-threshold-kmh', type=float, default=1)
    parser.add_argument('--minimum-voltage-v', type=float, default=1)
    parser.add_argument('--shutdown-voltage-v', type=float, default=10)
    args = parser.parse_args()
    result = run(args.source, args.output, Config(window_s=args.window_s, max_gap_s=args.max_gap_s,
                 moving_threshold_kmh=args.moving_threshold_kmh, minimum_voltage_v=args.minimum_voltage_v,
                 shutdown_voltage_v=args.shutdown_voltage_v))
    print(f"Consumed Wh: {result['metrics']['consumed_wh']:.6f}; Wh/km: {result['metrics']['wh_per_km']}")
    print(f"Predictive modeling: {result['modeling']['status']}; artifacts: {args.output.resolve()}")


if __name__ == '__main__':
    main()
