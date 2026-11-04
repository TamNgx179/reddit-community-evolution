A1 + A2 — FULL-STUDY FINAL-WINDOW DIAGNOSTICS

Source:
- export/predictions_final.csv
- export/features_all.csv
- export/labels_status_all.csv

Implementation:
- Uses reddit_sna.evaluation.diagnostics.forecast_tables().
- No model is fitted or refitted.
- Each model and seed remains separate.
- Uses label_month for monthly evaluation.
- Fixed six-class Macro-F1; absent classes receive zero_division=0 behavior.
- Confusion matrix: rows are true labels, columns are predicted labels.

A1:
- Monthly and overall Macro-F1.
- Per-class precision, recall, F1 and support.
- Confusion matrices by month and overall.

A2:
- Size strata.
- Lineage-history strata.
- Member-activity-history strata.
- Joint size × lineage-history strata.

Important:
- size_band includes singleton separately from the four requested bands.
- history_missing is lineage history, not member-activity history.
- Seeds are repeat runs, not independent communities.
- Unresolved and censored targets are not converted into event labels.
- Final predictions cover 1,269 unique samples, not all 7,490 resolved samples.
- Validation candidate predictions are not pooled with final predictions.
