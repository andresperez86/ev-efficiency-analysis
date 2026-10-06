# Analysis policies and exclusion ledger

1. Read the source CSV as UTF-8 with optional BOM. Preserve row order and source CSV row numbers.
2. Localize naive timestamps to fixed UTC-05:00. Invalid timestamps fail ingestion explicitly; do not guess or reorder.
3. Missing/invalid numeric fields become nonfinite values with named quality flags. No imputation is performed.
4. An interval is excluded from primary accounting if either endpoint has nonfinite speed, trip, voltage, current or power; invalid voltage <=1 V; negative speed; or power versus V*I disagreement exceeding max(1 W, 1% of absolute power).
5. A trailing stationary run with abs(voltage)<=10 V and speed<=1 km/h is shutdown/post-run. Exclude all touching intervals, including the transition boundary. EIA has a clear 48 V to <10 V stationary collapse at 21:57:16.334578. Sensitivity at 1/10/40 V is exported.
6. Exclude nonpositive timestamp differences, gaps >5 seconds, and negative trip increments. Never bridge missing intervals for primary metrics.
7. Negative power/current are flagged. On otherwise valid intervals, clip endpoint power to zero for consumed energy. Never report recovered/regenerative energy. Do not convert negative electrical values to their absolute values.
8. A sensitivity calculation excludes intervals touching any negative power/current sample. Its energy and distance denominators both change and its coverage is reported.
9. Integrate clipped endpoint power with a trapezoid over actual elapsed seconds; use interval trip increments over the same valid support. Raw signed integration includes shutdown and is only a diagnostic.
10. Split valid intervals at the linearly interpolated 1 km/h speed crossing for moving/stopped accounting. Trip is linearly apportioned within an interval. This is a low-rate approximation.
11. Report time-weighted mean/peak clipped power and current, time-weighted mean/std and extrema of voltage. Raw electrical samples remain in descriptive plots and quality tables.
12. Fixed-time periods begin at the first source timestamp. Eligibility requires a complete window, >=90% accepted duration, and positive accepted distance. Export all periods and their eligibility, including incomplete and stationary periods.
13. Acceleration proxy = change in quantized speed /3.6 / actual time difference. An event is a contiguous run at >=0.5 m/s² or <=-0.5 m/s²; runs reset across invalid intervals and at window boundaries. Stop count is the number of stationary bouts intersecting the window, including a bout already in progress at its start. Counts are not global race events.
14. Average speed and speed variance integrate piecewise-linear speed. Median and percentile speed approximate duration-weighted interval-midpoint samples. Speed bands are [0,16), [16,32), [32,40), [40,infinity) km/h.
15. Electrical high-demand duration is not an explanatory feature because it is constructed from target channels. Peak/mean electrical demand is descriptive only.
16. Pearson/Spearman ranks use mean absolute association while retaining signs and disagreement flags. Block bootstrap draws contiguous three-period blocks, never across excluded period IDs, with 300 draws and seed 42. Suppress bootstrap intervals for binary features with fewer than three observations at either level, and retain an explicit sparse-feature warning. Intervals are exploratory and not multiplicity adjusted; block length is not estimated from the process.
17. Optional modeling uses a strict driving-feature allowlist, three expanding forward splits, a one-period gap and seed 42. RF: 200 trees, maximum depth 5, minimum leaf size 3. MI is estimated on training folds; permutation importance uses held-out MAE and 30 repeats. SHAP uses training background only and held-out explanations. Check predictive skill against a training-mean baseline before interpreting model rankings.
18. Raw and mostly-moving subsets are both reported. <=5% stopped is a sensitivity policy, not permission to sacrifice race pace. No causal or strategy conclusion follows from importance alone.
19. Related CSV inspection records only filenames, schemas, row counts and lap-ID availability. Competition score units and cross-team comparability are not assumed.
20. GPS variables are provisional. No laps are reconstructed until coordinate order/reference system, finish-line geometry and validation evidence are confirmed.

Every primary accounting exclusion is recorded in `interval_ledger.csv`. Original
fields and sample flags remain in `sample_quality_flags.csv`. Configuration and
source SHA-256 are retained in the manifest. Statistical IQR counts are diagnostic
only; they neither exclude nor modify samples.
