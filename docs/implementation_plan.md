# Phase-one implementation plan

Reported to the user before creating project code:

1. Inspect EIA and related competition CSV schemas without modifying source data.
2. Define units, quality flags, dictionary, accounting policies and source provenance.
3. Write failing pytest accounting tests; implement typed ingestion, flags and interval metrics; rerun and review.
4. Write failing feature/correlation tests; implement nonoverlapping period summaries, descriptive rankings and pace comparisons.
5. Add optional MI/RF/permutation/SHAP analysis with forward-time validation and a strict explanatory allowlist.
6. Write an end-to-end export/source-preservation test before pipeline implementation.
7. Save reproducible tables, figures, JSON reports, manifest and assumptions.
8. Review physical interpretation, shutdown boundaries, ratio coupling, sparse predictors and window sensitivity.
9. Document validation and pending dependencies; propose Qt architecture without implementation.

Review refined shutdown detection from the <=1 V plateau to the full stationary
voltage-collapse tail (<=10 V). A mostly-moving sensitivity analysis was added
because terminal coasting had the lowest raw period Wh/km at an uncompetitive pace.
No lap reconstruction was undertaken.
