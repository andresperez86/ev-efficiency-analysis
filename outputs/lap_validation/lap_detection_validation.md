# Updated finish-line detection validation

Only endpoint B changed in the detector module. All crossing, direction,
sampling, movement, 30-second minimum-interval and 50-meter spatial-rearm logic
remain unchanged. No energy integration, efficiency analysis or feature
importance was run. Source: `C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv`. SHA-256: `33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`.

A: (4.954031331051374, -74.02100721093194). Previous B: (4.954114777761632, -74.02094657622197). Confirmed updated B: (4.954141279215972, -74.02090858842605).
WGS84 local east/north approximation at A; geographic degrees are not treated
as meters. No automatic extension, tolerance or coordinate correction applied.

| Metric | Previous segment | Updated segment |
|---|---:|---:|
| Length, m | 11.418144 | 16.354278 |
| Geometric intersections | 2 | 12 |
| Race-direction crossings | 1 | 11 |
| Valid after all unchanged rules | 1 | 11 |
| Rejected candidates | 1 | 1 |
| Complete crossing-to-crossing intervals | 0 | 10 |
| Partial recording segments | 2 | 2 |

## Geometric verdict

The updated segment is nondegenerate and captures a plausible recurring
sequence, but it is **not yet a fully validated single-lap boundary**.
It captures **10 of the 12 previous recurring near misses**.
Two still cross the supporting infinite line beyond B, never the finite segment.
Ten boundary-complete intervals exist, of which eight are plausible single laps
and two may each span two physical laps. They are marked ambiguous explicitly;
no missed pass is promoted to an accepted crossing.

Every valid crossing is left-to-right relative to directed A→B (direction −1).
The only reverse candidate is rejected by wrong direction, <30-second separation
and lack of 50-meter rearming. Crossing direction is consistent at both boundaries
of every reconstructed interval; direction consistency does not cure missing finishes.
An independent audit confirms >=30-second separation and a trustworthy GPS
sample >=50 m from the finite segment between every consecutive valid crossing.

## Remaining misses

| Previous miss | Old distance beyond B, m | New distance beyond B, m | New finish fraction | Time, UTC−05:00 |
|---|---:|---:|---:|---|
| 5 | 5.257973 | 0.283108 | 1.017311 | 2025-11-07T21:37:53.832154-05:00 |
| 11 | 5.409945 | 0.374567 | 1.022903 | 2025-11-07T21:51:29.559430-05:00 |

Finish fraction >1 means beyond endpoint B. The distances are measured in the local metric projection.

## Crossing and lap validation table

Lap number describes the interval **ending** at each crossing; crossing 1 has no preceding complete lap.

| Crossing | Interpolated time, UTC−05:00 | Previous crossing, s | Direction | Lap | Duration, s | Accepted trip distance, km | GPS distance, km | Full trip increment, km | Validation |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 2025-11-07T21:28:49.840599-05:00 | — | left_to_right | — | — | — | — | — | first_crossing_no_preceding_complete_lap |
| 2 | 2025-11-07T21:30:39.083993-05:00 | 109.243394 | left_to_right | 1 | 109.243394 | 1.218283 | 1.146210 | 1.218283 | plausible_single_lap |
| 3 | 2025-11-07T21:33:11.254422-05:00 | 152.170429 | left_to_right | 2 | 152.170429 | 1.215185 | 1.157178 | 1.215185 | plausible_single_lap |
| 4 | 2025-11-07T21:35:30.003275-05:00 | 138.748853 | left_to_right | 3 | 138.748853 | 1.217006 | 1.155928 | 1.217006 | plausible_single_lap |
| 5 | 2025-11-07T21:40:15.904527-05:00 | 285.901252 | left_to_right | 4 | 285.901252 | 2.436058 | 2.289577 | 2.436058 | ambiguous_possible_multiple_physical_laps |
| 6 | 2025-11-07T21:42:05.701971-05:00 | 109.797445 | left_to_right | 5 | 109.797445 | 1.212731 | 1.151548 | 1.212731 | plausible_single_lap |
| 7 | 2025-11-07T21:44:00.985686-05:00 | 115.283715 | left_to_right | 6 | 115.283715 | 1.206345 | 1.158619 | 1.206345 | plausible_single_lap |
| 8 | 2025-11-07T21:46:02.406507-05:00 | 121.420821 | left_to_right | 7 | 121.420821 | 1.206204 | 1.147247 | 1.206204 | plausible_single_lap |
| 9 | 2025-11-07T21:48:34.635725-05:00 | 152.229218 | left_to_right | 8 | 152.229218 | 1.224995 | 1.142799 | 1.224995 | plausible_single_lap |
| 10 | 2025-11-07T21:53:26.186466-05:00 | 291.550741 | left_to_right | 9 | 291.550741 | 2.425936 | 2.285433 | 2.425936 | ambiguous_possible_multiple_physical_laps |
| 11 | 2025-11-07T21:55:36.932904-05:00 | 130.746438 | left_to_right | 10 | 130.746438 | 1.211753 | 1.153531 | 1.211753 | plausible_single_lap |

## Rejected candidates

- Candidate 12, 2025-11-07T21:55:44.201582-05:00, 16.022772 km/h: `wrong_direction;minimum_crossing_interval;not_rearmed`; 7.268679 s since last accepted crossing.

## Partial segments and distance definitions

`partial_start`: 49.581508 s before crossing 1.
`partial_end`: 262.662648 s after the final accepted crossing.
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

Artifacts are isolated in `outputs/lap_validation/` to preserve the preceding
zero-lap efficiency outputs as historical. Use this updated validation rather
than the previous `outputs/reports/lap_detection_report.md` for current geometry.
The report and plot preserve both finish segments for comparison.

Further geometry or GPS-alignment evidence is required before whole-session
single-lap efficiency comparisons. The confirmed segment remains exact.
