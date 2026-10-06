# Validation and review

Validated environment: Python 3.13.16, pytest 9.1.1. No third-party analysis
libraries are required for the baseline pipeline.

## Test-first evidence

- Accounting tests were written before the package existed. First run failed
  collection with `ModuleNotFoundError: ev_analysis`; after implementation, all
  18 initial accounting cases passed.
- Feature/correlation tests were written before those modules. First run failed
  collection with `ModuleNotFoundError: ev_analysis.features`.
- The source-preserving deterministic export test preceded pipeline implementation
  and failed with `ModuleNotFoundError: ev_analysis.pipeline`.
- Review identified sparse binary predictors as unsuitable for reliable bootstrap
  intervals. A regression test first failed on the absent sparse warning; after
  implementation, intervals are explicitly suppressed for insufficient support.

Final suite: **30 passed, 1 skipped**. The skipped test exercises optional modeling
with a known signal and forward-time fold boundaries; NumPy/scikit-learn are absent.
Synthetic fixture tests check analytic values rather than comparing a function
with a copy of itself. The export test compares two runs, verifies SVG XML,
checks saved provenance, and confirms the original source hash is unchanged.

## Accounting cross-check

An independent direct CSV calculation reproduced consumed energy and trip distance
without calling the metric implementation. Moving plus stationary energy equals
total consumed energy, and moving plus stopped duration equals accepted duration.

Original source SHA-256 remains:

`33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`

## Coverage

`pytest-cov` was unavailable and could not be installed because outbound PyPI
connections were blocked. A standard-library `trace` line-coverage run and
annotated `.cover` files are saved under `outputs/coverage`; the module summary
is `outputs/reports/coverage_stdlib.json`. This is not branch coverage or a
pytest-cov measurement. The accounting module has 100% observed line coverage.
The predictive-method body is not covered because its dependencies are absent.

To reproduce the fallback line tracing:

```powershell
python -m trace --count --missing --coverdir outputs/coverage --module pytest -q -p no:cacheprovider
```

## Manual review findings

- Confirmed no regeneration assumption and retained every negative electrical flag.
- Confirmed energy and distance share interval support and actual timestamp spacing.
- Expanded shutdown to include the stationary low-voltage collapse, with exported threshold sensitivity.
- Retained stationary consumption before shutdown and rejected zero-distance efficiency.
- Checked the explanatory allowlist excludes electrical target components and target derivatives.
- Checked period boundaries partition energy without duplication and partial periods are ineligible.
- Noted startup/coasting effects, ratio coupling, quantized speed, sparse stops and window sensitivity.
- Confirmed no individual-row random split, lap reconstruction, GUI code or source-data modifications.
- Confirmed deterministic exports and explicit missing-method statuses.

Optional MI/RF/permutation/SHAP code still requires execution and review in an
environment with dependencies installed. Full multi-method validation is therefore
unfinished. The notebook scaffold has not been executed. SVGs were checked for
well-formed XML; a rendered visual review was not available in this environment.
