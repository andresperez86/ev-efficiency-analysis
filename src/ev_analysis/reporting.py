"""Stable JSON/CSV exports, dictionary, and stakeholder findings."""

import csv
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .ingestion import COLUMNS, NUMERIC


def serializable(value: Any) -> Any:
    if isinstance(value, float) and not isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(serializable(value), indent=2, sort_keys=True, allow_nan=False) + '\n', encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    columns = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: serializable(row.get(k)) for k in columns})


def dictionary(quality: dict) -> list[dict]:
    meanings = {
        "timestamp": ("datetime", "UTC-05:00", "Analysis timestamp in local competition time", "Integration", "Original preprocessing method undocumented"),
        "car_velocity": ("float", "km/h", "Vehicle speed", "Explanatory", "Seven quantized levels; sensor calibration undocumented"),
        "car_trip": ("float", "km", "Cumulative trip distance", "Target denominator", "Use interval increments; do not subtract origin from energy independently"),
        "car_voltage": ("float", "V", "Electrical voltage", "Descriptive and quality", "Measurement location unknown; final near-zero values are shutdown"),
        "car_current": ("float", "A", "Electrical current; positive means discharge", "Target construction and descriptive", "No regeneration; negative values are flagged artifacts until explained"),
        "power": ("float", "W", "Electrical power, numerically equal to voltage times current", "Target construction and descriptive", "Clip negative values to zero only on quality-valid support"),
        "gps_1": ("float", "degrees (provisional)", "Likely latitude", "GPS exploratory only", "Coordinate order/reference system and finish line require confirmation"),
        "gps_2": ("float", "degrees (provisional)", "Likely longitude", "GPS exploratory only", "Stationary jitter; not the primary distance source"),
        "timestamp_original": ("datetime text", "UTC-05:00", "Timestamp before preprocessing", "Provenance", "Matches timestamp in this file"),
        "retroceso_detectado": ("boolean text", "none", "Preprocessing reversal flag", "Provenance", "Exact preprocessing definition undocumented; constant False"),
        "segmento": ("integer text", "none", "Preprocessing segment identifier", "Provenance", "Constant 1; not a lap identifier"),
    }
    rows = []
    for column in COLUMNS:
        dtype, unit, meaning, role, caveat = meanings[column]
        observed = quality['numeric'].get(column, {})
        rows.append({"column": column, "canonical_field": NUMERIC.get(column, column), "type": dtype,
                     "unit": unit, "meaning": meaning, "analysis_role": role, "caveat": caveat,
                     "missing_count": quality['missing_values'][column],
                     "constant": column in quality['constant_columns'],
                     "observed_min": observed.get('min'), "observed_max": observed.get('max'),
                     "nonfinite_count": observed.get('nonfinite_count', 0)})
    return rows


def findings(quality: dict, metrics: dict, comparisons: dict, relationships: list[dict], modeling: dict,
             sensitivity: list[dict]) -> str:
    lines = ['# EIA telemetry findings', '',
             'This report describes one session and fixed-time operating periods, not reconstructed laps. Associations do not establish causality.', '',
             f"Source: {quality['rows']} rows, {quality['columns']} columns; {quality['time_start']} to {quality['time_end']}.",
             f"Missing fields: {sum(quality['missing_values'].values())}; duplicate rows: {quality['duplicate_rows']}; backward trip increments: {quality['trip_decreases']}.",
             f"Sampling seconds (min/median/mean/max): {quality['sampling_interval_s'].get('min')} / {quality['sampling_interval_s'].get('median')} / {quality['sampling_interval_s'].get('mean')} / {quality['sampling_interval_s'].get('max')}. Nonpositive intervals: {quality['nonpositive_intervals']}.",
             f"Nonfinite numeric values: {sum(v['nonfinite_count'] for v in quality['numeric'].values())}; constant columns: {quality['constant_columns']}.",
             f"Observed speed levels (km/h): {quality['speed_levels_kmh']}. Shutdown begins: {quality['shutdown_start']}.",
             f"Flags: {json.dumps(quality['quality_flag_counts'], sort_keys=True)}.",
             'Speed is heavily quantized. Derivative features are proxies and event counts are threshold-dependent.',
             'Shutdown and intervals touching invalid voltage are excluded. Negative electrical values are never interpreted as regeneration.', '',
             '## Energy accounting', '',
             f"Consumed energy: {metrics['consumed_wh']:.6f} Wh; valid distance: {metrics['distance_km']:.6f} km.",
             f"Wh/km: {metrics['wh_per_km']}; moving-only Wh/km: {metrics['moving_wh_per_km']}.",
             f"Stationary energy: {metrics['stationary_wh']:.6f} Wh; stopped time: {metrics['stopped_s']:.3f} s.",
             f"Valid-state average/peak power: {metrics['average_power_w']} / {metrics['peak_power_w']} W; average/peak clipped discharge current: {metrics['average_current_a']} / {metrics['peak_current_a']} A.",
             f"Valid-state voltage min/mean/max: {metrics['voltage_min_v']} / {metrics['voltage_mean_v']} / {metrics['voltage_max_v']} V.",
             f"Accepted intervals: {metrics['valid_interval_count']}; excluded: {metrics['excluded_interval_count']}; full-record time coverage: {metrics['coverage_fraction']}.",
             f"Raw signed energy diagnostic including post-run: {metrics['raw_signed_wh_diagnostic']:.6f} Wh. This is not consumed or recovered energy.", '',
             'Wh/km = sum of trapezoidal, nonnegative discharge energy over accepted intervals / sum of trip increments over the same intervals. Endpoint powers are clipped before piecewise-linear integration. Moving/stopped splits use linearly interpolated speed threshold crossings; trip distance is apportioned linearly within each original interval.', '',
             '## Descriptive candidate ranking', '',
             '| Rank | Candidate | Pearson | Spearman | Exploratory Spearman interval |',
             '|---|---|---|---|---|']
    for row in relationships:
        def fmt(value: float | None) -> str:
            return f'{value:.3f}' if value is not None else 'NA'
        lines.append(f"| {row['descriptive_rank']} | {row['feature']} | {fmt(row['pearson'])} | {fmt(row['spearman'])} | {fmt(row['spearman_block_bootstrap_p025'])} to {fmt(row['spearman_block_bootstrap_p975'])} |")
    lines += ['', 'Ranking score is the mean absolute Pearson/Spearman association. It is not a predictive ranking or an intervention recommendation. Speed bands, stopped percentage and speed summaries are correlated proxies. Speed/pace and Wh/km also share distance/time relationships; their association can partly reflect mathematical coupling.', '',
              '## Efficiency and performance', '', f"Eligible periods: {comparisons.get('eligible_count', 0)}."]
    if comparisons.get('eligible_count'):
        lines += [f"Most/least efficient period: {comparisons['most_efficient_period']} / {comparisons['least_efficient_period']}.",
                  f"Fastest/slowest period: {comparisons['fastest_period']} / {comparisons['slowest_period']}.",
                  f"Pareto periods: {comparisons['pareto_periods']}.",
                  f"Efficient quartile medians: {json.dumps(comparisons['efficient_quartile_medians'], sort_keys=True)}.",
                  f"Inefficient quartile medians: {json.dumps(comparisons['inefficient_quartile_medians'], sort_keys=True)}.",
                  'Pace-matched pairs are exported at a 2 km/h tolerance. They remain confounded by course position, elapsed session time and operating conditions. An acceptable pace floor must be selected by the racing team before recommending a strategy.']
    lines += ['', '## Sensitivity', '',
              '30/60/120-second window results and an alternative negative-artifact exclusion accounting are exported. The window origin is the first source timestamp. Thresholds are analysis policies, not confirmed sensor limits.',
              json.dumps(sensitivity, sort_keys=True), '', '## Predictive analysis status', '',
              f"Status: {modeling['status']}. See modeling.json for method availability and forward-block validation results.",
              'Mutual information, Random Forest, permutation importance and SHAP require optional dependencies. Missing methods have no fabricated scores.', '',
              '## Limitations and next steps', '',
              '- One session; no independent session-level validation. Periods may be serially dependent; block-bootstrap intervals are exploratory, not multiplicity adjusted.',
              '- No lap labels, start/finish line, temperatures, elevation, throttle or brake channels. GPS order and reference system are provisional.',
              '- Power is a target component. Current, power, energy, voltage and distance are excluded from the explanatory model allowlist.',
              '- Negative values may understate consumption after clipping. The sensitivity accounting excludes adjacent artifact intervals and reports coverage.',
              '- Default shutdown detection uses the trailing stationary run at voltage magnitude <=10 V, capturing the observed collapse before readings fall below 1 V. Sensitivity at 1/10/40 V is exported. The 10 V cutoff is a dataset-specific policy, not an engineering battery limit. No missing values are imputed and no long gaps are bridged.',
              '- Quantized speed limits acceleration interpretation. Median/percentile speed features are duration-weighted interval-midpoint approximations.',
              '- Sparse stop predictors are dominated by a few periods. The mostly-moving subset has only one period with nonzero stop count/time. Bootstrap intervals are suppressed for binary features with fewer than three observations in either level; these rankings are fragile.',
              '- Confirm GPS coordinate reference system and a directed finish-line segment. Then validate crossing-based laps with minimum crossing time, rearm distance and a GPS-jitter tolerance; discard incomplete first/last laps explicitly.',
              '- Collect more complete sessions and comparable laps; confirm electrical calibration and a race-pace floor before controlled driving experiments.', '']
    return '\n'.join(lines)
