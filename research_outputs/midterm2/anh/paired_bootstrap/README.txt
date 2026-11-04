PAIRED BOOTSTRAP — FULL-STUDY FINAL WINDOW

Scope:
- Final window only, label_month January–September 2018.
- 1,269 unique resolved samples per model/seed.
- Three seeds: 42, 43, 44.
- No model fitting or prediction regeneration.

Contrasts:
1. hier_lr_dynamic vs A_no_dynamics_matched
2. hier_lr_dynamic vs A_no_context_drift_matched
3. hier_lr_dynamic vs A_flat_matched

Methods:
- 1,000 paired calendar-month block bootstrap draws.
- Block length: 2 consecutive months.
- Macro-F1 uses fixed six classes.
- Seeds are averaged within each bootstrap draw, not treated as independent observations.
- Strata outcomes: both_correct, proposed_only, reference_only, both_wrong.
- Month-specific strata do not receive a month-block CI.
- Sparse strata may have dropped bootstrap draws.

Files:
- paired_cases.csv: paired sample-level outcomes.
- paired_macro_f1_intervals.csv: observed Macro-F1 deltas and bootstrap intervals.
- paired_strata_bootstrap.csv: paired outcome rates and intervals by strata.
- validation_audit.json: source hashes and run configuration.

Interpretation:
This is exploratory uncertainty analysis over nine final months.
It does not establish generalization across all 7,490 resolved samples.
A 95% bootstrap interval is not, by itself, proof of causal feature contribution.
