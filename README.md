# EV racing efficiency analysis

Auditable exploratory analysis of EIA racing telemetry. Analysis runs without
GUI dependencies; the future Qt interface will consume the same result files.
Original data is never edited or copied over.

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
