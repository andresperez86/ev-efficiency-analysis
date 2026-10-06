# EV racing efficiency analysis

Auditable exploratory analysis of EIA racing telemetry. Analysis runs without
GUI dependencies; the future Qt interface will consume the same result files.
Original data is never edited or copied over.

## Lap analysis

Current primary lap-efficiency analysis: `outputs/lap_km_per_wh/`, using
**km/Wh (higher is better)** and reciprocal Wh/km. Expected single-lap length
is approximately 1.21 km; actual measured distances are retained. Fresh detection
produces ten bounded intervals; eight satisfy the declared exploratory ±10%
trip/GPS distance screen, while double-length intervals 4/9 and partial segments
are excluded from every ranking. The same eight pass a ±5% trip screen. This
derived count is not an assumed eight-lap race: full physical lap count remains
unresolved where finish crossings were missed. Mean/median accepted single-lap
trip distance is 1.213909/1.213625 km. Validation, all required metrics, four
rankings and a time-versus-km/Wh Pareto plot are reproducible using
`scripts/compare_laps_km_per_wh.py` with `PYTHONPATH=src` in the virtual environment.
Previous Wh/km-primary reports below are historical.

Energy/pace comparison for the current exact finish geometry is now available
in `outputs/lap_energy_revision2/`: a complete metric table, energy/time rankings,
Pareto scatter and report. Intervals 4 and 9 remain geometrically ambiguous;
primary single-lap rankings exclude them, while separate all-interval rankings
and correlations retain them. No crossing or accounting policy changed.
With `PYTHONPATH=src`, reproduce using
`.venv\Scripts\python.exe scripts/analyze_lap_energy.py`.

Current endpoint B is now `(4.954155352342866, -74.02092561319948)`.
The second detection-only revision is in `outputs/lap_validation_revision2/`:
12 intersections, 11 valid crossings, 10 crossing-to-crossing intervals and
two partial segments. Two passes still miss beyond B by 0.321/0.480 m;
intervals 4 and 9 remain ambiguous possible multiple-lap intervals.
The validation script now compares against the immediately preceding B.
Current timing/distance statistics and both source/interpolated timestamps
are in that revision's report and `crossing_lap_validation.csv`.
Efficiency and modeling remain pending physical lap validation.

Previous detection-only validation (first confirmed endpoint B revision, 2026-10-06):
the updated segment gives 11 valid crossings and one rejected reverse candidate.
It captures 10 of 12 prior near misses; two still miss beyond B by 0.283/0.375 m.
There are 10 crossing-to-crossing intervals, including two ambiguous possible
multiple-lap intervals, and two partial segments. Current validation artifacts
are in `outputs/lap_validation/`; the efficiency exports below describe the
previous geometry and were not rerun. See
`outputs/lap_validation/lap_detection_validation.md` and
`crossing_lap_validation.csv`. With `PYTHONPATH=src`, reproduce detection-only
validation using `.venv\Scripts\python.exe scripts/validate_finish_geometry.py`.
Detector rules and energy accounting were not changed.

The finite finish segment supplied on 2026-10-06 is implemented in
`src/ev_analysis/laps.py`. The detector uses WGS84 local east/north coordinates,
directed finite-segment intersections, interpolated crossing timestamps, a
30-second minimum crossing interval, and 50-meter spatial rearming. It rejects
stationary crossings, line touches, wrong direction, excessive GPS speed and gaps.
Only consecutive accepted crossings bound complete laps; recording edges remain
explicit partial segments. Energy uses the existing validated accounting support.

```powershell
.venv\Scripts\python.exe -m pip install -e '.[test,laps]'
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m ev_analysis.lap_pipeline --source 'C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv' --output outputs
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Current result: **zero complete laps** with exact A–B. Twelve recurring passes
miss just beyond endpoint B; two actual intersections run in opposite directions.
The inferred race direction (`--direction -1`, left to right relative to A→B)
has one accepted crossing. This direction still needs independent confirmation.
No endpoint extension or proximity tolerance is applied. Corrected endpoints can
be passed as `--finish-a LAT LON --finish-b LAT LON`; inspect them before use.

Exports: `outputs/lap_crossings.csv`, `outputs/lap_summary.csv`,
`outputs/telemetry_with_laps.csv`, seven lap PNGs under `outputs/figures`, and
`outputs/reports/lap_detection_report.md`, `lap_efficiency_report.md`,
`lap_manifest.json`. `run_lap_analysis()` returns a pandas lap-level DataFrame.
Plots explicitly show unavailable comparisons when no complete laps exist.
Lap importance models remain gated by reconstruction validation. High-power
and high-current duration are descriptive measures, excluded from explanatory
models because they derive from the energy target channels.

The independent preimplementation inspection is reproducible with
`.venv\Scripts\python.exe scripts/inspect_lap_geometry.py`. It writes candidate
diagnostics and the geometry plot; rerun the lap pipeline afterward to restore
its validated-crossing report. Original baseline artifacts and their recorded
dependency status are historical; the lap environment now includes pandas and
Matplotlib, with versions recorded in the lap manifest.

## Reproduce the analysis

From this project directory in Windows PowerShell, with Python 3.11+:

```powershell
$env:PYTHONPATH = 'src'
python -m ev_analysis.pipeline --source 'C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv' --output outputs
python -m pytest -q -p no:cacheprovider
```

The baseline pipeline uses the standard library. Pytest is required for tests.
The validated environment is Python 3.13.16 with pytest 9.1.1. Configuration,
source SHA-256, runtime versions and method availability are saved in the manifest.
Use a separate output directory for each configuration or environment so artifacts
from previous optional modeling runs cannot be confused with the current run.

When network/package access is available, install test and modeling extras:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e '.[test,modeling]'
.venv\Scripts\python.exe -m pytest -q --cov=ev_analysis --cov-report=term-missing
.venv\Scripts\python.exe -m ev_analysis.pipeline --source 'C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv' --output outputs-modeling
```

Dependency installation failed in the creation environment because outbound PyPI
connections were blocked. Mutual information, Random Forest, permutation importance
and SHAP therefore have **no validated results yet**. Their optional implementation
and integration test are present; the test skips when dependencies are absent.
Baseline deterministic SVG figures are exported without Matplotlib.

## Results and artifacts

- `outputs/reports/findings.md`: quality, energy, descriptive ranking, comparisons and limitations.
- `outputs/reports/metrics.json`: session accounting, including moving/stationary energy and electrical summaries.
- `outputs/reports/quality.json`: timing, missingness, ranges, constants, quantization and flags.
- `outputs/reports/manifest.json`: source identity, policies, units, environment and status.
- `outputs/tables/data_dictionary.csv`: every source column, unit, role and caveat.
- `outputs/tables/sample_quality_flags.csv`: original fields plus flags; no silent row deletion.
- `outputs/tables/interval_ledger.csv`: accepted/excluded intervals and reasons.
- `outputs/tables/operating_periods.csv`: every period, including ineligible periods.
- `outputs/tables/candidate_associations*.csv`: Pearson/Spearman ranks and exploratory bootstrap intervals.
- `outputs/tables/correlation_matrix.csv`: both correlation methods for period variables.
- `outputs/reports/*sensitivity.json`: negative-artifact and shutdown-threshold sensitivity.
- `outputs/tables/periods_30s.csv`, `periods_60s.csv`, `periods_120s.csv`: window sensitivity.
- `outputs/figures/`: histograms, boxplots, traces, scatterplots, correlation matrix and pace trade-offs.

## Accounting contract

Speed: km/h; trip: km; voltage: V; current: A; power: W; local time: UTC-05:00.
Positive current means discharge. The vehicle has no regenerative braking.

For accepted interval endpoints, `consumption_power = max(power, 0)`. Consumed Wh
is the trapezoidal integral of this clipped endpoint power over actual elapsed
seconds, divided by 3600. Wh/km divides by the sum of trip increments over **the
same accepted intervals**. Zero distance yields an undefined metric (`null`),
never zero efficiency. Raw signed Wh is diagnostic only.

Default policies are in `docs/analysis_rules.md`. Thresholds are configurable via
CLI or the frozen `Config` object. The 10 V stationary terminal shutdown rule is
an observed-data policy, not a physical battery cutoff. No interpolation or
statistical outlier removal is performed. Endpoint interpolation for quadrature
and window splitting is a documented integration assumption, not missing-data imputation.

Moving-only energy/distance use speed >1 km/h, with linearly interpolated threshold
crossings. Stationary energy includes valid idling before shutdown. The stationary
distance portion is preserved separately through total minus moving distance.

## Interpretation

Power, current, voltage, Wh, target derivatives and trip distance are excluded
from the explanatory model allowlist. Speed summaries, stop exposure, speed-band
exposure and coarse acceleration/deceleration proxies are candidates, not causal
drivers. Ratio metrics have mathematical coupling with speed/pace.

Periods are nonoverlapping fixed-time blocks, not laps. Primary analysis uses
60 seconds; 30/120-second and mostly-moving (<=5% stopped) analyses assess
sensitivity. Mostly-moving is not a confirmed competitive pace threshold.
Forward-time model validation uses three expanding splits and a one-period gap.
No individual telemetry-row random split is used.

GPS order/reference system and a directed finish line remain unconfirmed. No lap
reconstruction or Qt GUI has been implemented. See `docs/qt_dashboard_architecture.md`.

## Development workflow

ECC's `python-testing` workflow guided red/green/refactor cycles. Accounting,
feature analysis and pipeline tests were written and observed to fail before
their modules existed, then implemented and reviewed. Tests include analytic
energy fixtures, invalid inputs, shutdown, missing values, timestamp anomalies,
long gaps, clipping, movement boundaries, correlations, leakage prevention,
Pareto selection and deterministic source-preserving exports.

See `docs/validation.md` for executed checks and the optional-modeling limitation.
