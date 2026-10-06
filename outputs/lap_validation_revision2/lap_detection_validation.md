# Updated finish-line detection validation

Only endpoint B changed in the detector module. All crossing, direction,
sampling, movement, 30-second minimum-interval and 50-meter spatial-rearm logic
remain unchanged. No energy integration, efficiency analysis or feature
importance was run. Source: `C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv`. SHA-256: `33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`.

A: (4.954031331051374, -74.02100721093194). Previous B: (4.954141279215972, -74.02090858842605). Confirmed updated B: (4.954155352342866, -74.02092561319948).
WGS84 local east/north approximation at A; geographic degrees are not treated
as meters. No automatic extension, tolerance or coordinate correction applied.

| Metric | Previous segment | Updated segment |
|---|---:|---:|
| Length, m | 16.354278 | 16.431290 |
| Geometric intersections | 12 | 12 |
| Race-direction crossings | 11 | 11 |
| Valid after all unchanged rules | 11 | 11 |
| Rejected candidates | 1 | 1 |
| Complete crossing-to-crossing intervals | 10 | 10 |
| Partial recording segments | 2 | 2 |

## Geometric verdict

The updated segment is nondegenerate and produces 11 recurring accepted crossings.
It captures **0 of 2 recurring near misses
from the immediately previous geometry**. Remaining misses: 2.
There are 10 boundary-complete intervals, including
8 plausible single laps and
2 ambiguous possible multiple-lap intervals.
Full-session single-lap validation is incomplete because recurring passes are still missed.
No missed pass is promoted to an accepted crossing.

Every valid crossing is left-to-right relative to directed A→B (direction −1).
The only reverse candidate is rejected by wrong direction, <30-second separation
and lack of 50-meter rearming. Crossing direction is consistent at both boundaries
of every reconstructed interval; direction consistency does not cure missing finishes.
An independent audit confirms >=30-second separation and a trustworthy GPS
sample >=50 m from the finite segment between every consecutive valid crossing.

## Remaining misses

| Previous miss | Old distance beyond B, m | New distance beyond B, m | New finish fraction | Time, UTC−05:00 |
|---|---:|---:|---:|---|
| 1 | 0.283108 | 0.320647 | 1.019514 | 2025-11-07T21:37:53.353150-05:00 |
| 2 | 0.374567 | 0.479925 | 1.029208 | 2025-11-07T21:51:28.439589-05:00 |

Finish fraction >1 means beyond endpoint B. The distances are measured in the local metric projection.

## Crossing and lap validation table

Lap number describes the interval **ending** at each crossing; crossing 1 has no preceding complete lap.

| Crossing | Source timestamp, UTC−05:00 | Interpolated time, UTC−05:00 | Previous crossing, s | Direction | Lap | Duration, s | Accepted trip distance, km | GPS distance, km | Full trip increment, km | Validation |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 2025-11-07T21:28:50.329497-05:00 | 2025-11-07T21:28:49.456747-05:00 | — | left_to_right | — | — | — | — | — | first_crossing_no_preceding_complete_lap |
| 2 | 2025-11-07T21:30:39.549989-05:00 | 2025-11-07T21:30:38.940559-05:00 | 109.483813 | left_to_right | 1 | 109.483813 | 1.218396 | 1.146276 | 1.218396 | plausible_single_lap |
| 3 | 2025-11-07T21:33:11.785932-05:00 | 2025-11-07T21:33:10.809878-05:00 | 151.869318 | left_to_right | 2 | 151.869318 | 1.214801 | 1.156783 | 1.214801 | plausible_single_lap |
| 4 | 2025-11-07T21:35:29.999845-05:00 | 2025-11-07T21:35:29.829024-05:00 | 139.019146 | left_to_right | 3 | 139.019146 | 1.217046 | 1.156233 | 1.217046 | plausible_single_lap |
| 5 | 2025-11-07T21:40:16.487457-05:00 | 2025-11-07T21:40:15.737943-05:00 | 285.908920 | left_to_right | 4 | 285.908920 | 2.436143 | 2.289449 | 2.436143 | ambiguous_possible_multiple_physical_laps |
| 6 | 2025-11-07T21:42:05.650471-05:00 | 2025-11-07T21:42:05.533548-05:00 | 109.795605 | left_to_right | 5 | 109.795605 | 1.212450 | 1.151492 | 1.212450 | plausible_single_lap |
| 7 | 2025-11-07T21:44:01.071867-05:00 | 2025-11-07T21:44:00.827620-05:00 | 115.294071 | left_to_right | 6 | 115.294071 | 1.206722 | 1.158802 | 1.206722 | plausible_single_lap |
| 8 | 2025-11-07T21:46:02.269734-05:00 | 2025-11-07T21:46:02.214160-05:00 | 121.386540 | left_to_right | 7 | 121.386540 | 1.205515 | 1.146933 | 1.205515 | plausible_single_lap |
| 9 | 2025-11-07T21:48:34.541702-05:00 | 2025-11-07T21:48:34.411741-05:00 | 152.197581 | left_to_right | 8 | 152.197581 | 1.225236 | 1.142631 | 1.225236 | plausible_single_lap |
| 10 | 2025-11-07T21:53:26.984071-05:00 | 2025-11-07T21:53:26.060849-05:00 | 291.649108 | left_to_right | 9 | 291.649108 | 2.426744 | 2.286388 | 2.426744 | ambiguous_possible_multiple_physical_laps |
| 11 | 2025-11-07T21:55:36.184520-05:00 | 2025-11-07T21:55:36.099035-05:00 | 130.038186 | left_to_right | 10 | 130.038186 | 1.211103 | 1.152093 | 1.211103 | plausible_single_lap |

## Lap statistics and anomalies

These statistics cover **all 10 crossing-to-crossing intervals**, including
any ambiguous intervals. They are not a claim that each interval is one physical lap.

- Median lap interval time: 134.528666 s.
- Minimum lap interval time: 109.483813 s.
- Maximum lap interval time: 291.649108 s.
- Median trip-derived interval distance: 1.215924 km.
- Median GPS-derived interval distance: 1.154163 km.
- Anomalous interval numbers: [4, 9].

Anomaly flags are diagnostic only; they do not change crossings or omit laps.
They flag an uncaptured recurring pass, time above the inclusive-quartile IQR
upper fence (205.063005 s), or trip distance above its upper fence
(1.241656 km).

| Interval | Duration, s | Trip distance, km | GPS distance, km | Missed passes inside | Interpretation |
|---|---:|---:|---:|---:|---|
| 4 | 285.908920 | 2.436143 | 2.289449 | 1 | ambiguous_possible_multiple_physical_laps |
| 9 | 291.649108 | 2.426744 | 2.286388 | 1 | ambiguous_possible_multiple_physical_laps |

## Rejected candidates

- Candidate 12, 2025-11-07T21:55:44.661215-05:00, 8.631407 km/h: `wrong_direction;minimum_crossing_interval;not_rearmed`; 8.562180 s since last accepted crossing.

## Partial segments and distance definitions

`partial_start`: 49.197656 s before crossing 1.
`partial_end`: 263.496517 s after the final accepted crossing.
Neither is automatically called Lap 1 or a complete lap.

`lap_distance_km` is the accepted trip increment using the existing interval
quality/shutdown rules, preserving the denominator for later energy accounting.
`trip_derived_distance_km` is the full interpolated boundary-to-boundary trip
increment. GPS distance sums clipped projected adjacent-sample segments, excluding
invalid GPS, gaps >5 s and interval GPS speeds >30 m/s. Coverage columns accompany
both distance supports. No energy was integrated. Negative electrical readings
retain their prior flags and are never interpreted as regeneration.

The long intervals are not implausible race pace by default: their roughly doubled
distance and an uncaptured recurring pass inside each indicate missed finish
detections. These are boundary-complete intervals, not validated single physical laps.

Artifacts are isolated in `outputs/lap_validation_revision2/` to preserve prior validation
and efficiency outputs as historical. Use this updated validation rather
than the previous `outputs/reports/lap_detection_report.md` for current geometry.
The report and plot preserve both finish segments for comparison.

Further geometry or GPS-alignment evidence is required before whole-session
single-lap efficiency comparisons. The confirmed segment remains exact.
