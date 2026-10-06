# Validation and review

## Expected-distance validation and km/Wh correction (2026-10-06)

Detection and accounting rules remain unchanged. Eleven accepted crossings
produce ten bounded intervals; a declared exploratory ±10% measured trip/GPS
distance consistency screen around 1.21 km retains eight single-lap intervals,
with no predefined count. The two double-length intervals are excluded from
all rankings, correlations and Pareto selection. Partial start/end segments are
reported separately; their shutdown/excluded duration is explicit.

The primary efficiency metric is km/Wh. Checks verify the reciprocal identity,
raw distance deviations, count relationships, ranking direction, invalid-ID
exclusion, per-lap accounting support and source SHA-256. A tighter ±5% trip
screen yields the same retained IDs. Forty-four existing accounting/lap tests
passed; the export test was deselected. The updated scatter was rendered and
visually reviewed. No race lap count was inferred by dividing distance by 1.21,
no missing crossing was invented, and no feature-importance model was run.

## Authorized energy/pace comparison with current geometry (2026-10-06)

All ten crossing-to-crossing intervals were accounted using existing lap metrics.
Their timestamps and source/geometry provenance were checked against the prior
validation table. Intervals 4 and 9 remain ambiguous and are excluded from the
primary eight-lap comparison; all-interval sensitivity results are also saved.
No physical crossing was invented or moved. Energy/distance sums partition
first-to-last accepted crossing support, shutdown samples are absent, and
source SHA-256 is unchanged. Negative power never reduces consumption.

An independent NumPy trapezoidal calculation from the CSV, using clipped
original endpoint powers and interpolated lap boundaries, matched per-interval
Wh within 5.86e-8 Wh and trip distance within 8.41e-9 km. Forty-four existing
accounting/lap tests passed; one export test was deselected. The Pareto scatter
was rendered and reviewed. Correlations are descriptive associations; no real
feature-importance or efficiency-driver models were run. These accounting
checks do not resolve the outstanding physical-lap ambiguity.

## Second confirmed endpoint B revision: detection-only (2026-10-06)

Detector endpoint B alone changed to `(4.954155352342866, -74.02092561319948)`.
Algorithm and accounting bodies were not edited. The existing detector still
finds 12 candidates, accepts 11 left-to-right crossings and rejects one reverse
candidate for direction, spacing and rearming. Both previously missed passes
remain outside the finite segment (0.320647/0.479925 m beyond B).
The ten crossing-to-crossing intervals include two ambiguous multiple-lap
intervals; physical single-lap validation remains incomplete.

Independent checks confirm 30-second spacing, 50-meter spatial rearming, and
unchanged source SHA-256. Nineteen selected existing geometric/assignment tests
passed; six export/energy/efficiency tests were deselected for this focused run.
The rendered trajectory/finish/crossing plot was reviewed. Current artifacts
are under `outputs/lap_validation_revision2/`, preserving earlier validation
outputs. All-interval timing/distance statistics and diagnostic anomaly flags
are recorded without changing detection. No real efficiency or importance
analysis was performed.

## Confirmed endpoint B revision: detection-only validation (2026-10-06)

Only `FINISH_B` changed in the detector module; detector and accounting logic
remain unchanged. The detection-only validation script compares old/new segments,
exports accepted and rejected candidates and a distance-only validation table,
and checks the original source hash. It does not run the efficiency pipeline.
The existing 25 lap tests passed after the coordinate replacement.

The new segment yields 12 geometric candidates, 11 valid left-to-right crossings,
one rejected reverse crossing, ten boundary-complete intervals and two partial
segments. It captures ten of twelve prior near misses. Two still fall beyond B
by 0.283108/0.374567 m; intervals 4 and 9 may each span multiple physical laps.
Thus geometry is nondegenerate and substantially improved, but full-session
single-lap validation remains incomplete. All valid directions agree, and an
independent audit verifies 30-second separation and 50-meter spatial rearming.
The rendered plot shows both finish segments, valid/rejected candidates and an
endpoint detail of both remaining misses. New artifacts are isolated under
`outputs/lap_validation/`; no real efficiency/importance analyses were rerun.

## Lap extension validation (2026-10-06)

Independent source inspection and rendered finish-line plots preceded changes
to implementation code. The finite segment produced two opposite-direction
candidates; twelve recurring race-direction passes miss beyond endpoint B.
Only one candidate is accepted under the inferred race direction, leaving
zero complete laps. This is a conservative detector outcome, not validation
of the physical finish geometry or independent confirmation of race direction.

The new geometric/accounting test file was run before `ev_analysis.laps` existed
and failed collection with `ModuleNotFoundError`. After implementation,
analytic tests covered projection, finite intersection, direction, oscillations,
endpoint touches, duplicates, 30-second spacing, 50-meter rearming, partial
segments, interpolated timing, distance, irregular-time energy and Wh/km.
A rearm boundary case exposed floating-point error at exactly 50 m; a documented
one-micrometer numerical tolerance resolved it. The source-preserving export
test first failed on the absent `ev_analysis.lap_pipeline`, then passed.
Crossing-boundary accounting conserves energy and keeps its trip denominator
on identical accepted support, including invalid-electrical exclusions.

Lap tests: **25 passed**. Full suite in the project virtual environment:
**56 passed**, with three third-party SHAP plotting deprecation warnings.
The formerly skipped optional period-modeling test now runs on a synthetic
known-signal fixture; this does not validate models on real reconstructed laps.
No real lap importance models were run. Source hash remains unchanged.
Requested PNGs were generated; geometry plots were visually reviewed. Empty
lap comparison/profile charts explicitly communicate zero complete laps.
The lap manifest records runtime and plotting package versions.

The original baseline validation record below describes the earlier environment.

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
