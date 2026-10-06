# Contexto de la conversación

## Estructura solicitada

```text
ev-efficiency-analysis/
├── docs/
│   └── chat_context.md
├── src/
├── tests/
└── README.md
```

Las carpetas `docs/`, `src/` y `tests/`, y el archivo `README.md` ya
existían al recibir esta estructura. Se añadió este documento conservando
el contenido existente del proyecto.

## Referencias del proyecto

- [README](../README.md): propósito, ejecución y resultados del análisis.
- [Reglas del análisis](analysis_rules.md): criterios y políticas.
- [Plan de implementación](implementation_plan.md).
- [Validación](validation.md).
- [Arquitectura del dashboard Qt](qt_dashboard_architecture.md).

## Lap-analysis request and preflight (2026-10-06)

- User supplied the exact physical finish segment: A =
  (latitude 4.954031331051374, longitude -74.02100721093194), B =
  (latitude 4.954114777761632, longitude -74.02094657622197).
- Source remains
  `C:/Users/ANDRÉS PÉREZ/Projects/ResultadosGP_limpios/datos_limpios/EIA_clean.csv`.
  `gps_1` is latitude and `gps_2` is longitude, supported by observed ranges;
  WGS84 remains an assumption pending metadata confirmation.
- Finite-segment inspection found two opposite-direction intersections.
  The inferred race direction is left to right relative to directed A→B.
  Twelve recurring passes in that direction miss beyond B by 0.073–5.410 m.
  Only one exact intersection occurs in that direction: zero complete laps
  can currently be reconstructed under the requested rules.
- No finish-line extension or tolerance is authorized. Geometry clarification
  remains pending. See [lap detection report](../outputs/reports/lap_detection_report.md).
- Requested detector rules: moving crossing, finite segment intersection,
  valid race direction, minimum 30 seconds between accepted crossings,
  and 50 m spatial rearming. Interpolate crossing timestamps; retain
  rejected candidates and reasons. Label recording edges `partial_start`
  and `partial_end`; only crossing-to-crossing intervals are complete laps.
- Existing no-regeneration and matched-support electrical accounting decisions
  remain in force. Electrical high-demand durations remain descriptive,
  because they are constructed from target channels.
- A conservative detector and boundary-clipped lap metrics were subsequently
  implemented with pytest-first evidence. The requested CSVs, seven PNGs and
  reports are exported, with zero complete laps for the supplied exact geometry.
  Feature importance and meaningful lap comparisons remain pending finish-line
  validation. See `src/ev_analysis/laps.py` and `src/ev_analysis/lap_pipeline.py`.

## Confirmed finish endpoint revision and detection-only validation (2026-10-06)

- The user explicitly replaced B with confirmed coordinates
  (latitude 4.954141279215972, longitude -74.02090858842605). A is unchanged.
  This supersedes the preceding B coordinate; all detector logic and energy
  rules remain unchanged. No automatic finish extension has been applied.
- Detection-only results: 12 geometric candidates, 11 left-to-right valid
  crossings, and one reverse candidate rejected for wrong direction, less than
  30 seconds since the previous crossing, and no 50-meter rearming.
- Ten of the twelve former near misses are captured. Two still miss B by
  0.283108 m and 0.374567 m along the supporting line. All accepted directions
  agree, but the finish segment still does not capture every recurring pass.
- There are ten complete crossing-to-crossing intervals and two partial recording
  segments. Eight intervals are plausible single physical laps; intervals 4 and
  9 contain an uncaptured pass and roughly double distance, so are ambiguous
  possible multiple-lap intervals. They must not be interpreted as single-lap
  efficiency results without resolving those missed boundaries.
- New validation artifacts are isolated in `outputs/lap_validation/`, preserving
  previous efficiency artifacts as historical. Current report:
  [finish geometry validation](../outputs/lap_validation/lap_detection_validation.md).
  Reproduce with `.venv/Scripts/python.exe scripts/validate_finish_geometry.py`
  after setting `PYTHONPATH=src`.
- No source CSV changes, real lap-efficiency analysis or feature importance were
  performed for this revision. Further finish/GPS validation remains pending.

## Second confirmed endpoint B revision (2026-10-06)

- The user replaced B again: (latitude 4.954155352342866,
  longitude -74.02092561319948). This is the current authoritative endpoint.
  A, crossing algorithm, 30-second minimum interval, 50-meter rearming and
  energy-accounting rules are unchanged. No line extension is authorized.
- Detection remains 12 geometric intersections, 11 accepted left-to-right
  crossings, one reverse candidate rejected, ten boundary-complete intervals,
  and two partial recording segments. All accepted directions agree.
- Neither of the two misses from the immediately previous geometry is captured.
  They now miss beyond B by 0.320647 m and 0.479925 m (previously
  0.283108/0.374567 m). Intervals 4 and 9 remain ambiguous multiple-lap candidates.
- Statistics across all ten intervals, including those ambiguities: median time
  134.528666 s, minimum 109.483813 s, maximum 291.649108 s; median trip-derived
  distance 1.215924 km and median GPS-derived distance 1.154163 km.
- Current artifacts: `outputs/lap_validation_revision2/`, including raw and
  interpolated timestamps in `crossing_lap_validation.csv`, a plot, comparison
  of both remaining misses, report and manifest. Previous revision artifacts
  in `outputs/lap_validation/` remain historical and were preserved.
- Detection-only validation and 19 selected geometric/assignment tests passed.
  Source hash is unchanged; no real efficiency/importance analysis was run.
  Physical single-lap reconstruction remains incompletely validated.

## Authorized lap energy and pace comparison (2026-10-06)

- User explicitly requested energy/pace metrics, rankings, Pearson/Spearman
  correlation and Pareto analysis with the current exact finish geometry.
  The ten accepted-crossing intervals were analyzed without changing boundaries
  or accounting. Intervals 4 and 9 retain their geometric ambiguity.
- All-interval metrics are retained. Primary physical single-lap comparisons
  use the eight plausible intervals, preserving their original lap IDs. Separate
  all-interval rankings and correlations show the sensitivity to ambiguities.
- Fastest lap 1: 109.483813 s and 15.994670 Wh/km; this is also the highest
  Wh/km among plausible single laps. Most efficient lap 8: 9.832480 Wh/km
  at 152.197581 s. Lap 5 is 0.311792 s slower than lap 1 with 15.3299% lower Wh/km.
- Pareto set: 1, 2, 3, 5, 7, 8, 10 (same including ambiguous intervals).
  Pearson/Spearman: -0.104748/-0.587879 over all ten intervals,
  versus -0.894841/-0.976190 over eight plausible single laps. Associations
  are descriptive, not causal; physical lap validation remains incomplete.
- Artifacts: `outputs/lap_energy_revision2/`; reproduce with
  `PYTHONPATH=src` and `.venv/Scripts/python.exe scripts/analyze_lap_energy.py`.
  Source SHA-256 unchanged. Partial/shutdown intervals excluded, negative power
  clipped at original endpoints on accepted support, actual timestamps used.
  No feature-importance or efficiency-driver model was run.

## Expected lap length and primary efficiency correction (2026-10-06)

- User confirmed approximate physical lap length of 1.21 km, not a lap count.
  No predefined number of laps may be assumed. The exact finish line remains
  unchanged; the measured trip/GPS distances are not rescaled to 1.21 km.
- Fresh detection gives 11 valid crossings and ten bounded intervals. Eight
  satisfy single-lap distance/coverage checks; intervals 4 and 9 are approximately
  double length (+101.334%/+100.557% trip deviations), hence excluded from every
  ranking, correlation and Pareto plot. IDs are preserved, not renumbered.
  Eight is a derived count of validated single-lap intervals, not the total race
  lap count. The total physical race lap count is unresolved due to missed finishes.
- Explicit exploratory distance tolerance is ±10% for trip and GPS estimates.
  All retained trip distances are within -0.371% to +1.259% of the reference;
  a ±5% trip-distance screen selects the same IDs. GPS distances are 4.23–5.57%
  below 1.21 km and are reported separately as corroborating chord estimates.
- Primary metric is now measured accepted trip km / consumed Wh, higher better.
  Wh/km remains reciprocal engineering consumption, lower better. Existing
  clipping, validated electrical support and actual timestamp integration remain.
- Valid interval mean/median trip distance: 1.213909/1.213625 km.
  Fastest/least efficient: lap 1 (109.483813 s, 0.062521 km/Wh).
  Most efficient: lap 8 (0.101704 km/Wh). Near-fastest Pareto compromise: lap 5,
  0.311792 s slower than lap 1 with 18.105% higher km/Wh.
- Pareto IDs: 1, 2, 3, 5, 7, 8, 10. Pearson/Spearman time vs km/Wh:
  +0.903229/+0.976190 on valid single laps only. Faster laps show lower km/Wh
  in this session; association is not causation. No causal/driver model was run.
- Current canonical artifacts: `outputs/lap_km_per_wh/`, including validation
  with full timestamps/deviations, partial segment report, required eight-column
  primary table, detailed power/current metrics, four rankings, scatter and manifest.
  Reproduce: `PYTHONPATH=src`, then run `scripts/compare_laps_km_per_wh.py` in the venv.
