# EIA telemetry findings

This report describes one session and fixed-time operating periods, not reconstructed laps. Associations do not establish causality.

Source: 1917 rows, 11 columns; 2025-11-07T21:28:00.259091-05:00 to 2025-11-07T21:59:59.595552-05:00.
Missing fields: 0; duplicate rows: 0; backward trip increments: 0.
Sampling seconds (min/median/mean/max): 1.000903 / 1.001459 / 1.001741367954071 / 1.227965. Nonpositive intervals: 0.
Nonfinite numeric values: 0; constant columns: ['retroceso_detectado', 'segmento'].
Observed speed levels (km/h): [0.0, 8.05254912, 16.10509824, 24.157647359999995, 32.21019648, 40.2627456, 48.31529471999999]. Shutdown begins: 2025-11-07T21:57:16.334578-05:00.
Flags: {"invalid_voltage_state": 135, "negative_current": 5, "negative_power": 90, "negative_voltage": 85, "shutdown_post_run": 164}.
Speed is heavily quantized. Derivative features are proxies and event counts are threshold-dependent.
Shutdown and intervals touching invalid voltage are excluded. Negative electrical values are never interpreted as regeneration.

## Energy accounting

Consumed energy: 189.497868 Wh; valid distance: 14.642218 km.
Wh/km: 12.941882280960854; moving-only Wh/km: 12.924247838176845.
Stationary energy: 0.322829 Wh; stopped time: 109.509 s.
Valid-state average/peak power: 388.69720745814413 / 1229.67039728983 W; average/peak clipped discharge current: 8.064195868494881 / 24.8196104141361 A.
Valid-state voltage min/mean/max: 46.205895092013314 / 49.04518789448169 / 52.55489884823146 V.
Accepted intervals: 1752; excluded: 164; full-record time coverage: 0.9144170069512372.
Raw signed energy diagnostic including post-run: 189.497504 Wh. This is not consumed or recovered energy.

Wh/km = sum of trapezoidal, nonnegative discharge energy over accepted intervals / sum of trip increments over the same intervals. Endpoint powers are clipped before piecewise-linear integration. Moving/stopped splits use linearly interpolated speed threshold crossings; trip distance is apportioned linearly within each original interval.

## Descriptive candidate ranking

| Rank | Candidate | Pearson | Spearman | Exploratory Spearman interval |
|---|---|---|---|---|
| 1 | stop_count | -0.474 | 0.203 | -0.094 to 0.578 |
| 2 | acceleration_pct | -0.319 | -0.346 | -0.622 to 0.018 |
| 3 | acceleration_event_count | -0.340 | -0.294 | -0.570 to 0.083 |
| 4 | deceleration_pct | -0.400 | -0.161 | -0.533 to 0.320 |
| 5 | deceleration_event_count | -0.372 | -0.142 | -0.533 to 0.360 |
| 6 | max_speed_kmh | 0.361 | 0.057 | -0.486 to 0.353 |
| 7 | speed_std_kmh | 0.394 | 0.000 | -0.528 to 0.216 |
| 8 | speed_40_plus_pct | 0.161 | 0.227 | -0.085 to 0.559 |
| 9 | stopped_pct | 0.139 | 0.232 | -0.094 to 0.578 |
| 10 | p90_speed_kmh | 0.298 | 0.065 | -0.334 to 0.448 |
| 11 | speed_16_32_pct | -0.154 | -0.201 | -0.585 to 0.073 |
| 12 | average_speed_kmh | 0.044 | 0.114 | -0.187 to 0.480 |
| 13 | median_speed_kmh | 0.002 | 0.117 | -0.194 to 0.484 |
| 14 | p10_speed_kmh | -0.015 | 0.078 | -0.180 to 0.395 |
| 15 | speed_0_16_pct | 0.009 | 0.037 | -0.378 to 0.385 |
| 16 | speed_32_40_pct | 0.016 | 0.012 | -0.347 to 0.305 |

Ranking score is the mean absolute Pearson/Spearman association. It is not a predictive ranking or an intervention recommendation. Speed bands, stopped percentage and speed summaries are correlated proxies. Speed/pace and Wh/km also share distance/time relationships; their association can partly reflect mathematical coupling.

## Efficiency and performance

Eligible periods: 29.
Most/least efficient period: 28 / 0.
Fastest/slowest period: 1 / 28.
Pareto periods: [1, 14, 16, 18, 19, 21, 28].
Efficient quartile medians: {"acceleration_pct": 25.035970000000038, "average_speed_kmh": 30.633853621916163, "speed_std_kmh": 6.410388284361813, "stopped_pct": 0.0, "wh_per_km": 9.84788375635255}.
Inefficient quartile medians: {"acceleration_pct": 20.053365000000365, "average_speed_kmh": 22.681641679716094, "speed_std_kmh": 6.072653845125858, "stopped_pct": 0.0, "wh_per_km": 16.017871699848722}.
Pace-matched pairs are exported at a 2 km/h tolerance. They remain confounded by course position, elapsed session time and operating conditions. An acceptable pace floor must be selected by the racing team before recommending a strategy.

## Sensitivity

30/60/120-second window results and an alternative negative-artifact exclusion accounting are exported. The window origin is the first source timestamp. Thresholds are analysis policies, not confirmed sensor limits.
[{"eligible_periods": 57, "top_three_associations": ["deceleration_pct", "deceleration_event_count", "stop_count"], "window_s": 30.0}, {"eligible_periods": 29, "top_three_associations": ["stop_count", "acceleration_pct", "acceleration_event_count"], "window_s": 60.0}, {"eligible_periods": 14, "top_three_associations": ["speed_0_16_pct", "stopped_pct", "speed_16_32_pct"], "window_s": 120.0}]

## Predictive analysis status

Status: dependencies_unavailable. See modeling.json for method availability and forward-block validation results.
Mutual information, Random Forest, permutation importance and SHAP require optional dependencies. Missing methods have no fabricated scores.

## Limitations and next steps

- One session; no independent session-level validation. Periods may be serially dependent; block-bootstrap intervals are exploratory, not multiplicity adjusted.
- No lap labels, start/finish line, temperatures, elevation, throttle or brake channels. GPS order and reference system are provisional.
- Power is a target component. Current, power, energy, voltage and distance are excluded from the explanatory model allowlist.
- Negative values may understate consumption after clipping. The sensitivity accounting excludes adjacent artifact intervals and reports coverage.
- Default shutdown detection uses the trailing stationary run at voltage magnitude <=10 V, capturing the observed collapse before readings fall below 1 V. Sensitivity at 1/10/40 V is exported. The 10 V cutoff is a dataset-specific policy, not an engineering battery limit. No missing values are imputed and no long gaps are bridged.
- Quantized speed limits acceleration interpretation. Median/percentile speed features are duration-weighted interval-midpoint approximations.
- Sparse stop predictors are dominated by a few periods. The mostly-moving subset has only one period with nonzero stop count/time. Bootstrap intervals are suppressed for binary features with fewer than three observations in either level; these rankings are fragile.
- Confirm GPS coordinate reference system and a directed finish-line segment. Then validate crossing-based laps with minimum crossing time, rearm distance and a GPS-jitter tolerance; discard incomplete first/last laps explicitly.
- Collect more complete sessions and comparable laps; confirm electrical calibration and a race-pace floor before controlled driving experiments.

## Mostly-moving sensitivity

This optional descriptive subset accepts periods with at most 5% stopped time; it is not a confirmed competitive pace floor.

Eligible periods: 26. Leading associations: speed_16_32_pct (Pearson=-0.30088698410264225, Spearman=-0.34177223190227163), speed_40_plus_pct (Pearson=0.29840634018158163, Spearman=0.30719223117678085), stop_count (Pearson=0.2936860366448867, Spearman=0.30666666666666664), stopped_pct (Pearson=0.2936860366448866, Spearman=0.30666666666666664), speed_std_kmh (Pearson=-0.24753296936104943, Spearman=-0.3292307692307692).

The lowest raw period Wh/km can occur in terminal coasting. Inspect pace and operating state before interpreting efficiency rankings. Window-size sensitivity shows whether candidate ordering is stable.

Mostly-moving efficient quartile medians: {'wh_per_km': 10.242511847494296, 'average_speed_kmh': 31.254306620991102, 'stopped_pct': 0.0, 'speed_std_kmh': 7.001190712450106, 'acceleration_pct': 25.870000000000033}. Inefficient quartile medians: {'wh_per_km': 15.8623098194916, 'average_speed_kmh': 35.96628174654594, 'stopped_pct': 0.0, 'speed_std_kmh': 5.883356985961839, 'acceleration_pct': 21.71137000000035}. Lower consumption in these groups can accompany lower pace; the trade-off needs matched-lap validation.
