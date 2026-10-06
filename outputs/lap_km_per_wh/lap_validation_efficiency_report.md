# Distance-validated lap efficiency in km/Wh

## Count and validation first

No race lap count is assumed. The exact finite finish line produces 12
geometric candidates and 11 valid same-direction crossings, delimiting
10 complete crossing-to-crossing intervals. Of these, 8 satisfy
the single-lap distance/coverage criteria; 2 are invalid or unresolved
single-lap intervals. The full physical race lap count is unresolved because
the finite line still misses two recurring passes. No virtual finish, automatic
line extension, splitting into assumed laps or renumbering has been applied.

Expected distance is approximately 1.21 km, not a replacement for measured
distance. An explicit exploratory ±10.0% consistency screen is used
for both trip and GPS estimates (not a confirmed engineering tolerance). Trip distance
is the primary accounting distance. Tightening the trip screen to ±5% gives the
same IDs: [1, 2, 3, 5, 6, 7, 8, 10]. The retained trip estimates
are all within roughly 1.3% of 1.21 km; GPS chord distances are systematically
lower and are independently displayed. Coverage must be >=90%, with no shutdown
samples in an eligible lap. Long/short distances are flagged, never corrected.

| Interval ID | Start timestamp | End timestamp | Time s | Trip km | GPS km | Trip deviation % | GPS deviation % | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | 2025-11-07T21:28:49.456747-05:00 | 2025-11-07T21:30:38.940559-05:00 | 109.484 | 1.218396 | 1.146276 | +0.694 | -5.266 | validated_single_lap |
| 2 | 2025-11-07T21:30:38.940559-05:00 | 2025-11-07T21:33:10.809878-05:00 | 151.869 | 1.214801 | 1.156783 | +0.397 | -4.398 | validated_single_lap |
| 3 | 2025-11-07T21:33:10.809878-05:00 | 2025-11-07T21:35:29.829024-05:00 | 139.019 | 1.217046 | 1.156233 | +0.582 | -4.444 | validated_single_lap |
| 4 | 2025-11-07T21:35:29.829024-05:00 | 2025-11-07T21:40:15.737943-05:00 | 285.909 | 2.436143 | 2.289449 | +101.334 | +89.211 | invalid_or_unresolved_interval |
| 5 | 2025-11-07T21:40:15.737943-05:00 | 2025-11-07T21:42:05.533548-05:00 | 109.796 | 1.212450 | 1.151492 | +0.202 | -4.835 | validated_single_lap |
| 6 | 2025-11-07T21:42:05.533548-05:00 | 2025-11-07T21:44:00.827620-05:00 | 115.294 | 1.206722 | 1.158802 | -0.271 | -4.231 | validated_single_lap |
| 7 | 2025-11-07T21:44:00.827620-05:00 | 2025-11-07T21:46:02.214160-05:00 | 121.387 | 1.205515 | 1.146933 | -0.371 | -5.212 | validated_single_lap |
| 8 | 2025-11-07T21:46:02.214160-05:00 | 2025-11-07T21:48:34.411741-05:00 | 152.198 | 1.225236 | 1.142631 | +1.259 | -5.568 | validated_single_lap |
| 9 | 2025-11-07T21:48:34.411741-05:00 | 2025-11-07T21:53:26.060849-05:00 | 291.649 | 2.426744 | 2.286388 | +100.557 | +88.958 | invalid_or_unresolved_interval |
| 10 | 2025-11-07T21:53:26.060849-05:00 | 2025-11-07T21:55:36.099035-05:00 | 130.038 | 1.211103 | 1.152093 | +0.091 | -4.786 | validated_single_lap |

## Partial recording segments (excluded)

- `partial_start`: 2025-11-07T21:28:00.259091-05:00 to 2025-11-07T21:28:49.456747-05:00, 49.198 s; accepted trip 0.011759 km, excluded duration 0.000 s.
- `partial_end`: 2025-11-07T21:55:36.099035-05:00 to 2025-11-07T21:59:59.595552-05:00, 263.497 s; accepted trip 0.056302 km, excluded duration 164.263 s.

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
| 1 | 109.484 | 1.218396 | 19.487843 | 0.062521 | 15.994670 | 40.019 | 1229.670 |
| 2 | 151.869 | 1.214801 | 13.134667 | 0.092488 | 10.812196 | 28.931 | 1215.578 |
| 3 | 139.019 | 1.217046 | 15.410817 | 0.078974 | 12.662475 | 31.479 | 1142.254 |
| 5 | 109.796 | 1.212450 | 16.419846 | 0.073841 | 13.542703 | 39.798 | 1080.378 |
| 6 | 115.294 | 1.206722 | 16.430221 | 0.073445 | 13.615581 | 37.848 | 1012.797 |
| 7 | 121.387 | 1.205515 | 15.656857 | 0.076996 | 12.987688 | 35.811 | 1015.250 |
| 8 | 152.198 | 1.225236 | 12.047113 | 0.101704 | 9.832480 | 28.795 | 962.331 |
| 10 | 130.038 | 1.211103 | 15.706860 | 0.077107 | 12.969055 | 33.673 | 919.172 |

`lap_metrics.csv` also contains start/end timestamps, maximum speed, average discharge power, average current and peak current.

## Rankings (validated single laps only)

- highest_km_per_Wh: [8, 2, 3, 10, 7, 5, 6, 1].
- fastest_lap: [1, 5, 6, 7, 10, 3, 2, 8].
- lowest_Wh_per_km: [8, 2, 3, 10, 7, 5, 6, 1].
- lowest_energy_Wh: [8, 2, 3, 7, 10, 5, 6, 1].

## Performance and efficiency

Mean measured trip lap distance: 1.213909 km.
Median measured trip lap distance: 1.213625 km.
Mean/median GPS lap distance: 1.151405/1.151793 km.
Pearson lap time vs km/Wh: 0.903229.
Spearman lap time vs km/Wh: 0.976190.
In these validated intervals, longer times tend to accompany higher km/Wh,
so faster laps tend to be less efficient. This is association, not causation;
small single-session samples and operating conditions limit interpretation.
Pearson must be recomputed for the reciprocal metric, not merely sign-flipped.

Pareto-efficient laps minimize time and maximize km/Wh: [1, 2, 3, 5, 7, 8, 10].
Fastest lap: 1; most efficient: 8;
least efficient: 1.
The closest-in-time Pareto alternative to the fastest lap is
lap 5: 0.311792 s slower,
18.105% higher km/Wh and
15.330% lower Wh/km.
This is a useful observed compromise, not a uniquely optimal strategy;
a team-selected pace/energy preference is needed to choose among Pareto points.

The scatter plot uses time on x and km/Wh on y: upper-left is fast/efficient,
lower-left fast/inefficient, upper-right efficient/slow, lower-right slow/inefficient.
No invalid/partial interval is plotted as a ranked lap.

Source SHA-256: `33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`. Detector, finish geometry and electrical
accounting rules are unchanged. No feature-importance model was run.
