# Lap efficiency report

Consumed Wh integrates max(endpoint power,0) over actual elapsed seconds with
trapezoidal quadrature, after established electrical quality/shutdown exclusions.
Boundary clipping preserves the original clipped-endpoint linear power function.
There is no recovered energy or regenerative braking. Negative readings are
flagged; raw signed Wh is diagnostic only. No original data is modified.

Primary `lap_distance_km` is accepted trip distance over the same support as
consumed energy. `trip_distance_km` is the complete boundary-to-boundary trip
increment. GPS distance has its own gap/jump-filtered coverage. Their difference
is reported without treating GPS as an authoritative odometer. Coverage must
be inspected before comparisons. Zero accepted distance produces undefined Wh/km.

Speed statistics follow existing time-weighted piecewise-linear conventions;
median is a duration-weighted midpoint approximation. Discrete-level exposure
uses nearest observed-level regions, not exact instantaneous plateau time.
Event counts reset at lap boundaries and invalid intervals. Cruising requires
moving speed and acceleration magnitude below 0.5 m/s². High-power and current
thresholds are exploratory policies (default 800 W/20 A), not engineering limits.
Quality sample counts use timestamps in [lap start,lap end); touching interval
exclusions still affect both sides of each boundary.

Electrical high-demand durations are descriptive relationships only. They remain
excluded from explanatory importance because they use target channels. Driving
features are candidate associations, not causal interventions. Race pace and
Wh/km may be mathematically coupled; the lowest-energy lap is not automatically
the best strategy. Pareto selection minimizes both Wh/km and lap duration among
laps with >=90% accepted accounting duration and positive accepted distance.

**Zero complete laps.** Lap rankings, relationships, Pareto selection and
importance cannot be estimated. The five comparison/profile PNGs explicitly
show this status. Resolve finish geometry before interpreting lap behavior.

MI, Random Forest, permutation importance and SHAP were **not run**: lap reconstruction requires validation before modeling.
