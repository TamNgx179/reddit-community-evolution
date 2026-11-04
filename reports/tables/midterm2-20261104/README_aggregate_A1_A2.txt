A1 + A2 — AGGREGATED FINAL-WINDOW RESULTS

Source:
- analysis_outputs_20261104_A1_A2_run2/

Aggregation:
- Three seeds: 42, 43, 44.
- Arithmetic mean across seeds.
- Sample standard deviation (ddof=1).
- Support and n are retained once after checking equality.
- Support is not multiplied by three.
- No model is fitted or refitted.

A1:
- Overall Macro-F1 and accuracy.
- Monthly Macro-F1 and accuracy.
- Per-class precision, recall and F1.
- Overall per-class F1 visualization.

A2:
- Community size.
- Lineage history.
- Member activity history.
- Joint size × lineage-history strata.
- Stratified combined tables.

Figures:
- Overall model ranking with sample SD error bars.
- Monthly Macro-F1 heatmap.
- Overall per-class F1 heatmap.
- Size and history Macro-F1 heatmaps.

Important:
- Results use final-window predictions only.
- Final sample count is 1,269.
- Unresolved and censored targets are not predictive labels.
- Seeds are repeat runs, not independent samples.
- Original per-seed confusion matrices remain unchanged.
- SD=0 means identical metric values across these three seeds;
  it does not establish general model certainty.
