# Lap detection report

Source: `C:\Users\ANDRÉS PÉREZ\Projects\ResultadosGP_limpios\datos_limpios\EIA_clean.csv`; 1917 rows. SHA-256: `33cebf917f2008f5f666dc5763f5cfc90d6409222b776ef988f33f75781ade78`.
Original columns: timestamp, car_velocity, car_trip, car_voltage, car_current, power, gps_1, gps_2, timestamp_original, retroceso_detectado, segmento.
Latitude `gps_1` range: 4.9540055 to 4.9553155.
Longitude `gps_2` range: -74.021286 to -74.01873616.
Finish A: (4.954031331051374, -74.02100721093194); B: (4.954114777761632, -74.02094657622197); finite length 11.418144 m.
Projection: WGS84 local east/north tangent approximation at A; datum is assumed.
GPS-polyline distance to line is zero where true candidate intersections exist;
nearest recorded GPS point distance is 0.42585594009153377 m.
Timestamp spacing min/median/max: 1.000903/1.001459/1.227965 s.
Approximate median sampling frequency: 0.998543125579779 Hz.
Nonpositive timestamp gaps: 0; gaps above policy: 0.
Maximum GPS interval speed: 20.854475 m/s.
Intervals above GPS jump threshold: 0.
Repeated consecutive GPS pairs: 0.
Maximum reported vehicle speed: 48.315295 km/h.
GPS speed exceeding reported vehicle speed merits calibration/jitter review;
the exploratory jump threshold is not proof of positional accuracy.
GPS jump policy: reject interval-implied speed >30 m/s; no interpolation across
invalid coordinates, nonpositive time differences or gaps >5.0 s.

Candidate intersections: 2. Accepted under selected direction: 1.
Complete laps: 0. Direction: -1 (left to right relative to A→B).
Direction independently confirmed: False.
For the supplied EIA geometry, preflight inferred left-to-right from recurring
passes. It found twelve passes beyond B by 0.073–5.410 m, so the physical segment
is nondegenerate but does not reliably span the recorded racing path. The reverse
candidate occurs amid stop/start readings. See `lap_geometry_preflight.json` and
`finish_line_near_misses.csv` for the independent preimplementation inspection.
No infinite-line crossing, endpoint extension or proximity tolerance is accepted.

| Candidate | Interpolated timestamp | Speed km/h | Direction | Accepted | Reason |
|---|---|---:|---|---|---|
| 1 | 2025-11-07T21:53:26.100002-05:00 | 40.262746 | left_to_right | True | accepted |
| 2 | 2025-11-07T21:55:44.531194-05:00 | 10.722270 | right_to_left | False | wrong_direction |

Only finite transverse intersections count. The crossing must be moving (>1 km/h),
in the selected direction, at least 30 seconds after the previous accepted
crossing, and armed by a trustworthy GPS sample at least 50 meters away from
the finite finish segment (numerical tolerance 1 micrometer). A line touch with
no confirmed side change is rejected. Rearming is spatial distance from the
line, not cumulative path length. Rejected candidates do not reset these rules.
Crossing time, GPS location, speed and trip are interpolated within the original
adjacent interval. `timestamp` is the right-hand source timestamp;
`interpolated_timestamp` is the crossing timestamp. Timestamps use UTC−05:00.

Telemetry labels use half-open lap intervals: before first crossing is
`partial_start`, after final crossing is `partial_end`, between accepted
crossings is `complete`. With no crossings use `unassigned_no_crossing`.
With one crossing there are two partial segments and zero complete laps.
`crossing_id` is the most recent accepted crossing, not a nearest-sample event.
`distance_into_lap` and `distance_into_lap_km` use trip increments in km;
these per-sample annotations are descriptive, not the accounting denominator.

See `detected_crossings.png` and `gps_track_finish_line.png` for visual review.
The supplied exact geometry requires clarification before claiming validated
race laps. Models remain gated; acceptance here is conditional on direction.
