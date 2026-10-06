# Future Qt Designer / PySide6 dashboard

This document is a design proposal. There is no GUI code or reconstructed lap data.

The desktop interface will consume the analysis package and saved artifacts.
Typed result objects and immutable configuration belong to analysis code. Qt
controllers manage selection and display; they contain no cleaning, integration,
feature or model formulas. A CLI and notebook call the same pipeline.

| View | Inputs and interaction |
|---|---|
| Session summary | Consumed Wh, distance, Wh/km, pace, moving/stopped exposure, coverage, source identity |
| Quality flags | Filter original rows and interval ledger by flag, exclusion and timestamp; display threshold policies |
| Time-series explorer | Linked time range for speed, trip, voltage, current, power; shade shutdown and invalid intervals |
| Lap comparison | Disabled until validated lap reconstruction exists; show distance-aligned traces and lap metrics afterward |
| Efficiency versus pace | Pareto scatter; user-defined acceptable pace floor; distinguish periods from laps |
| Variable relationships | Scatter, grouped distributions, signed correlations and nonlinear descriptive views |
| Feature-importance comparison | Method-specific scores, validation folds, baseline skill and unavailable-method status |
| Efficient versus inefficient behavior | Matched-pace period/lap comparisons; show course and operating-condition limitations |
| Export | Save current selection, configuration, tables and figures with provenance |

Designer `.ui` forms will define the layouts. PySide6 can load them through
[QUiLoader](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/uifiles.html).
Future package: `gui/controllers`, `gui/models`, `gui/workers`, `gui/plots`; forms in `ui/`.

Use a QObject worker moved to QThread for analysis jobs. Workers emit progress,
result and error signals; only the GUI thread updates widgets. Cancellation checks
occur between stages. GUI selection state is separate from immutable analysis
results; cached results are keyed by source hash and full configuration.

Proposed lap method after confirmation: project GPS to local metric coordinates,
detect a directed segment crossing the finite finish-line segment, interpolate
crossing time, enforce minimum lap time and require rearming outside a metric
distance zone. Reject crossings near invalid GPS or long gaps; retain rejected
crossing candidates and reasons. Validate against manually marked crossings and
known times. Exclude partial first/last laps explicitly and test noise, hovering,
double crossings, opposite direction, gaps and boundary energy partitioning.

GPS exists in EIA and related telemetry but no lap IDs were found. A results table
contains team/event scores, not confirmed per-lap timing. Lap reconstruction is
potentially feasible after finish-line and coordinate confirmation; accuracy
cannot be established from this dataset alone.

Model documentation:
[permutation importance and correlated features](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html),
[mutual information](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_regression.html),
[SHAP TreeExplainer](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html).
