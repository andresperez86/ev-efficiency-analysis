# Lap energy and pace comparison

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
| 1 | 21:28:49.456747-05:00 | 21:30:38.940559-05:00 | 109.484 | 1.218396 | 19.487843 | 15.994670 | 40.019 | 48.315 | 640.791 | 1229.670 | plausible_single_lap |
| 2 | 21:30:38.940559-05:00 | 21:33:10.809878-05:00 | 151.869 | 1.214801 | 13.134667 | 10.812196 | 28.931 | 48.315 | 311.352 | 1215.578 | plausible_single_lap |
| 3 | 21:33:10.809878-05:00 | 21:35:29.829024-05:00 | 139.019 | 1.217046 | 15.410817 | 12.662475 | 31.479 | 48.315 | 399.074 | 1142.254 | plausible_single_lap |
| 4 | 21:35:29.829024-05:00 | 21:40:15.737943-05:00 | 285.909 | 2.436143 | 33.407104 | 13.713111 | 30.664 | 48.315 | 420.643 | 1144.108 | ambiguous_possible_multiple_physical_laps |
| 5 | 21:40:15.737943-05:00 | 21:42:05.533548-05:00 | 109.796 | 1.212450 | 16.419846 | 13.542703 | 39.798 | 48.315 | 538.377 | 1080.378 | plausible_single_lap |
| 6 | 21:42:05.533548-05:00 | 21:44:00.827620-05:00 | 115.294 | 1.206722 | 16.430221 | 13.615581 | 37.848 | 48.315 | 513.025 | 1012.797 | plausible_single_lap |
| 7 | 21:44:00.827620-05:00 | 21:46:02.214160-05:00 | 121.387 | 1.205515 | 15.656857 | 12.987688 | 35.811 | 48.315 | 464.340 | 1015.250 | plausible_single_lap |
| 8 | 21:46:02.214160-05:00 | 21:48:34.411741-05:00 | 152.198 | 1.225236 | 12.047113 | 9.832480 | 28.795 | 48.315 | 284.956 | 962.331 | plausible_single_lap |
| 9 | 21:48:34.411741-05:00 | 21:53:26.060849-05:00 | 291.649 | 2.426744 | 30.727168 | 12.661889 | 29.986 | 48.315 | 379.284 | 983.243 | ambiguous_possible_multiple_physical_laps |
| 10 | 21:53:26.060849-05:00 | 21:55:36.099035-05:00 | 130.038 | 1.211103 | 15.706860 | 12.969055 | 33.673 | 48.315 | 434.831 | 919.172 | plausible_single_lap |

## Rankings

Lowest Wh/km, plausible single laps: [8, 2, 3, 10, 7, 5, 6, 1].

Lowest Wh/km, all intervals (4/9 ambiguous): [8, 2, 9, 3, 10, 7, 5, 6, 4, 1].

Fastest time, plausible single laps: [1, 5, 6, 7, 10, 3, 2, 8].

Fastest time, all intervals (4/9 ambiguous): [1, 5, 6, 7, 10, 3, 2, 8, 4, 9].


## Correlation and tradeoff

| Population | n | Pearson (time vs Wh/km) | Spearman (time vs Wh/km) |
|---|---:|---:|---:|
| Plausible single laps, excluding 4/9 | 8 | -0.894841 | -0.976190 |
| All boundary-complete intervals | 10 | -0.104748 | -0.587879 |

These are descriptive associations, not causal effects. Small single-session
samples, course/operating state, unequal interval lengths and the Wh/km ratio
limit interpretation. No strategy recommendation follows from correlation alone.

Pareto-efficient plausible single laps: **[1, 2, 3, 5, 7, 8, 10]**, jointly minimizing
lap time and Wh/km. All-interval Pareto set: [1, 2, 3, 5, 7, 8, 10].
Fastest plausible lap: 1. Lowest Wh/km plausible lap:
8. The frontier offers observed tradeoffs; it does
not establish an optimal racing strategy without an acceptable race-pace floor.

The source SHA-256 remains `33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`. Summed interval energy and distance
were verified against the first-to-last-crossing accounting support. The manifest
preserves the unresolved ambiguity; this analysis does not declare intervals
4/9 validated physical laps.

Files: `lap_comparison.csv`, `lap_summary.csv`, `ranking_lowest_wh_per_km.csv`,
`ranking_fastest_lap.csv`, their `all_intervals_` counterparts,
`efficiency_vs_lap_time.png`, and `energy_comparison_manifest.json`.

## Practical comparison

Lap 1 is fastest (109.484 s), but has the highest
Wh/km among plausible single laps (15.994670 Wh/km).
It remains Pareto efficient because no other lap is faster.
Lap 8 has the lowest Wh/km (9.832480), at
152.198 s and 12.047113 Wh.
Lap 5 is a useful near-fastest tradeoff: only 0.311792 s slower than lap 1,
with 15.330% lower Wh/km. Lap 6 is dominated by lap 5, which is both
faster and lower in Wh/km. Laps 7, 10 and 3 give intermediate observed tradeoffs,
while 2 and 8 occupy the slower, lower-consumption end. These observations do
not establish that changing driving behavior causes the observed differences.
