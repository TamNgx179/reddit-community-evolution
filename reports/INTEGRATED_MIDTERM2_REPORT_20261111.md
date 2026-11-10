# Integrated Midterm 2 Report
## Community Evolution in Online Reddit Communities

**Reporting scope:** Full-study diagnostics, Week 4 model comparison, human review and tracker audit, and the separate H1 HeTCo pilot  
**Evidence cutoff:** 11 November 2026  
**Primary full-study model:** `hier_lr_dynamic`

> **Study-boundary note.** The full-study evaluation (1,269 community-month samples from January–September 2018) and the H1 HeTCo pilot (571 main-window samples from 2015) are separate studies with different reference labels and protocols. Their scores must not be pooled or placed in one model-ranking table. H1 does not replace or modify the full-study primary model.

---

# 1. Introduction and Research Questions

Online communities change over time as members join, leave, interact, and reorganize. This study examines whether structural events in detected online communities can be predicted from information available before the next monthly transition.

The prediction task uses six event classes: **stable, grow, shrink, merge, split, and dissolve**. The operational target is defined by the observed interaction graph, community detection, and the declared lineage/event-tracking rules. It should therefore be interpreted as a rule-based structural event label, rather than an unquestionable statement about the social identity or continued existence of a group.

The integrated analysis addresses four questions:

1. **Label applicability:** What proportion of observed community-month transitions receives a resolved event label, and how do resolved, unresolved, and terminally censored records differ?
2. **Predictive performance:** How does the proposed hierarchical logistic-regression model perform across the six classes, calendar months, community sizes, and history-availability strata?
3. **Comparative performance:** Does the proposed model outperform the hierarchical HGB comparator and matched controls on the same frozen evaluation cases, and where does it make different errors?
4. **Label interpretation and hypothesis testing:** How closely do submitted reviewer decisions agree with one another and with the frozen tracker, and does the separate H1 threshold ablation support its predicted mechanism?

The evidence is descriptive and comparative. It does not establish causal effects of features, universal superiority, or prospective performance on unseen future data.

# 2. Dataset and Graph Construction

The full study uses 15 Reddit corpora and 45 monthly snapshots from January 2015 through September 2018. Valid replies are represented as directed author-to-parent-author interactions, assigned to the UTC month of the child record. The undirected user projection aggregates reply counts in both directions.

Communities are detected independently in each monthly snapshot using weighted Leiden partitions. The declared GED adaptation compares member overlap and importance-weighted inclusion to establish transition links and community events. A directional inclusion of at least 0.5 accepts a lineage link. The declared dissolution threshold is 0.1; competing weak or ambiguous patterns can remain unresolved.

The prediction unit is a detected community at month *t*. Features are restricted to records available through *t*, while the target describes the transition from *t* to *t+1*. This cutoff is essential: later information must not be used to construct predictors for an earlier prediction point.

The resulting labels are operational outputs of the graph construction, community detection, and tracking rules. A tracker-assigned dissolve label means that the declared continuity procedure did not accept a successor under its rules; it does not independently prove that the underlying social group disappeared.

# 3. Labeling and Coverage

## 3.1 Overall label-resolution coverage

The full-study feature and label-status exports contain 11,745 community-month records:

| Status | Community-month records |
|---|---:|
| Resolved | 7,490 |
| Unresolved | 4,072 |
| Terminally censored | 183 |
| **Total** | **11,745** |

Community-month coverage is calculated over observed transitions, excluding terminally censored records from the denominator:

\[
\text{Coverage}=\frac{7,490}{7,490+4,072}=64.78\%.
\]

A separate member-month weighted measure is 1,417,626 / 1,787,503 = **79.31%**. These measures answer different questions: the first weights each community-month record equally, while the second weights by community membership. Repeated observations across months remain in both totals.

Terminally censored records are reported separately. They are not unresolved event labels and must not be converted into dissolve cases.

## 3.2 Coverage by size and history

Coverage differs across community-size groups:

| Community size | Resolved | Unresolved | Censored | Coverage |
|---|---:|---:|---:|---:|
| 2 | 4,810 | 2,770 | 130 | 63.46% |
| 3–4 | 1,569 | 828 | 34 | 65.46% |
| 5–20 | 737 | 227 | 6 | 76.45% |
| >20 | 374 | 247 | 13 | 60.23% |

By history availability:

| History flag | Resolved | Unresolved | Censored | Coverage |
|---|---:|---:|---:|---:|
| Available (`history_missing=0`) | 503 | 374 | 13 | 57.35% |
| Missing (`history_missing=1`) | 6,987 | 3,698 | 170 | 65.39% |

Coverage is highest in the 5–20 size band and lowest in the >20 band among the listed size strata. The available-history group has lower observed coverage than the missing-history group in this export. These are descriptive differences, not causal explanations.

## 3.3 Resolved versus unresolved feature profiles

The compared feature columns have no missing values within either the resolved or unresolved subsets. This is feature-value completeness; it is not the same as label-resolution coverage.

The size distribution is highly skewed. Resolved records have mean community size 189.27, while unresolved records have mean size 90.83; however, the median is 2 in both groups. Density means are approximately 0.803 for resolved and 0.828 for unresolved records. `past_window_fraction` equals 1.0 in both groups and does not distinguish the two statuses.

The large difference between means and medians indicates that a small number of large communities influence the average. Interpretation should therefore consider quartiles and stratified summaries, not means alone. The analysis did not produce formal standardized effect sizes or inferential tests such as SMD, KS tests, or Cramér's V. No causal interpretation is warranted.

## 3.4 Monthly coverage

Coverage varies by month rather than remaining constant. In the final prediction horizon, coverage is 66.67% in January 2018, 62.37% in February, 72.12% in March, 70.67% in April, 67.21% in May, 70.00% in June, 76.04% in July, 66.95% in August, and 71.50% in September. These monthly values describe the observed label population and should not be confused with model performance.

# 4. Evaluation Protocol

The full-study predictive evaluation uses the frozen final prediction window from January through September 2018. It contains **1,269 unique community-month cases per seed**, **19 model configurations**, and seeds **42, 43, and 44**.

The evaluation uses a fixed six-class label set: stable, grow, shrink, merge, split, and dissolve. Macro-F1 is calculated across all six classes with `zero_division=0`. Unresolved and terminally censored records are excluded from predictive metrics; neither is converted into an event class.

The saved prediction export was checked against the resolved label export and corresponding feature records. The evaluation report records that all evaluated predictions matched their expected labels and feature keys. No model was fitted or refitted for the diagnostic analyses summarized here.

The three seeds are repeated runs on the same evaluation cases, not independent test samples. Identical results across seeds for deterministic configurations must not be interpreted as evidence of stability under new sampling conditions.

# 5. Baselines and Proposed Methods

The primary full-study method is `hier_lr_dynamic`, a hierarchical logistic-regression configuration with dynamic features. The principal reference comparator is `hier_hgb_dynamic`. Other reference baselines include majority prediction, persistence, random forest, logistic regression, and matched boosting. Additional controls isolate hierarchy, dynamics, context drift, and static/dynamic feature choices.

The 19 configurations are retained in the frozen output inventory. The main comparisons in this report focus on the pre-declared proposed model, the hierarchical HGB comparator, and matched component controls. Historical or secondary controls are not treated as equivalent primary baselines.

The H1 threshold experiment belongs to a separate 2015 HeTCo pilot. It tests a decision-rule change for the HeTCo attention model and does not alter the full-study `hier_lr_dynamic` configuration.

# 6. Results and Error Analysis

## 6.1 Overall model comparison

| Model | Macro-F1 | Accuracy | Cases per seed |
|---|---:|---:|---:|
| `hier_lr_dynamic` (proposed) | **0.4117** | 0.9046 | 1,269 |
| `hier_hgb_dynamic` | 0.3880 | **0.9094** | 1,269 |
| `flat_lr_dynamic` | 0.3616 | 0.9496 | 1,269 |
| `B4_logreg` | 0.3311 | 0.9472 | 1,269 |
| `B2_random_forest` | 0.2565 | 0.1524* | 1,269 |
| `B5_matched_boosting` | 0.2330 | 0.1789 | 1,269 |
| `B1_majority` | 0.1597 | 0.9196 | 1,269 |
| `B1_persistence` | 0.1562 | 0.8605 | 1,269 |

*The report's baseline comparison lists the B2 accuracy mean as 0.1524; the per-seed values are approximately 0.151–0.155.*

The proposed model has the highest Macro-F1 among the listed primary reference models, but HGB has slightly higher accuracy. This is not contradictory. Dissolve represents 1,167 of 1,269 cases (91.96%), so sample-weighted accuracy is dominated by the majority class. The majority baseline achieves 91.96% accuracy but only 0.1597 Macro-F1. Macro-F1 is therefore the more informative metric for comparing performance across the six fixed classes.

The proposed model's Macro-F1 advantage over hierarchical HGB is 0.0237. This is an aggregate metric advantage, not evidence that the proposed model wins on more individual cases.

## 6.2 Per-class performance

| True class | Support | Proposed recall | Proposed F1 | HGB recall | HGB F1 |
|---|---:|---:|---:|---:|---:|
| stable | 4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| grow | 19 | 0.1579 | 0.0968 | 0.1579 | 0.1277 |
| shrink | 25 | 0.4800 | 0.4444 | 0.5600 | 0.4667 |
| merge | 15 | 0.2000 | 0.2308 | 0.2000 | 0.1132 |
| split | 39 | 0.6923 | 0.7397 | 0.5641 | 0.6567 |
| dissolve | 1,167 | 0.9452 | 0.9587 | 0.9529 | 0.9640 |

The proposed model is stronger on split and has a higher F1 for merge, while HGB has higher F1 for grow, shrink, and dissolve. Neither model correctly predicts any stable cases, although stable has only four examples. These small supports make rare-class estimates uncertain.

The proposed model predicts dissolve for 14 of 19 grow cases (73.7%) and 8 of 15 merge cases (53.3%). HGB predicts dissolve for 12 of 19 grow cases (63.2%) and 9 of 15 merge cases (60.0%). The central difficulty is therefore not simply distinguishing events from non-events in general; it is the dissolve-versus-event decision for sparse grow and merge classes.

## 6.3 Monthly and subgroup performance

For `hier_lr_dynamic`, monthly Macro-F1 ranges from 0.2445 in April 2018 to 0.5496 in August 2018. The month-to-month variation is descriptive; it does not establish a temporal trend. Rare classes may be absent or represented by very few cases in individual months.

By community size, the proposed model's Macro-F1 is 0.2078 for size 2 (n=857), 0.2380 for size 3–4 (n=239), 0.1658 for size 5–20 (n=97), and 0.3208 for size >20 (n=76). The pattern is not monotonic. The 5–20 stratum contains only dissolve cases in this final sample; under fixed six-class Macro-F1, absent classes receive zero F1, which depresses the stratum score.

By lineage history, Macro-F1 is 0.4246 when available (n=105) and 0.3933 when missing (n=1,164). By member-activity history, it is 0.4143 when available (n=730) and 0.2001 when missing or not recorded (n=539). These are not causal effects: the class composition and support differ between strata. Some joint strata are extremely small; for example, size 5–20 with lineage history available has one case.

## 6.4 Error analysis

For the proposed model (seed 42), class-level recall is 0.9452 for dissolve, 0.1579 for grow, 0.2000 for merge, 0.4800 for shrink, 0.6923 for split, and 0.0000 for stable.

Frequent misclassification pairs include:

| True class → Predicted class | Count |
|---|---:|
| dissolve → grow | 37 |
| grow → dissolve | 14 |
| dissolve → stable | 14 |
| split → shrink | 12 |
| merge → dissolve | 8 |
| dissolve → merge | 8 |
| shrink → split | 7 |

These errors reinforce the need to inspect class-level metrics. High accuracy is largely driven by the dominant dissolve class and conceals weak recall for grow, merge, and stable.

## 6.5 Week 4 paired correctness comparison

The Week 4 comparison evaluates the proposed model and comparators on identical keys. For `hier_lr_dynamic` versus `hier_hgb_dynamic`, each seed has:

| Paired outcome | Cases |
|---|---:|
| Both correct | 1,119 |
| Proposed only correct (wins) | 29 |
| HGB only correct (losses) | 35 |
| Both wrong | 86 |
| **Total** | **1,269** |

The proposed model therefore has **six net fewer individually correct cases** than HGB, despite its higher Macro-F1. The paired outcomes are identical for seeds 42, 43, and 44. This is an important adverse result and must not be omitted.

By class, the proposed model has a net +5 paired correctness advantage on split, net -2 on shrink, net -9 on dissolve, and zero net on grow and merge. The stable cases are all wrong for both models. This shows how a higher Macro-F1 can coexist with fewer total correct predictions: Macro-F1 gives equal weight to classes, whereas paired correctness counts each case equally.

Against `B4_logreg`, the proposed model has 16 wins and 70 losses (net -54). Against `flat_lr_dynamic`, it has 9 wins and 66 losses (net -57). Against `A_no_dynamics_matched`, it has 28 wins and 44 losses (net -16). Against `A_flat_matched`, it has 445 wins and 17 losses (net +428). These are paired case counts, not independent statistical tests.

The proposed-versus-HGB comparison has 95 cases with different predicted labels. The four-group audit accounts for 64 cases where exactly one model is correct (29 + 35); the remaining 31 differing predictions are both-wrong cases. No owner-predeclared target-case set was supplied. The 34 grow/merge cases are therefore a descriptive diagnostic subset, not a pre-registered target set. In that subset, both old and new evaluations correctly predict six cases and both predict dissolve for 22; no repairs or regressions are observed.

## 6.6 Full-study interpretation

The evidence supports a narrow conclusion: the proposed hierarchical LR dynamic model has the highest Macro-F1 among the primary full-study reference models, but it does not dominate HGB on case-level correctness or every class. The largest weaknesses remain the rare grow and merge classes and the four stable cases. The paired and class-level results should accompany the headline Macro-F1.

# 7. Human Review, Adjudication, Tracker Comparison, and Lineage

## 7.1 Reviewer agreement and provenance

The diagnostic panel contains 60 stratified cases. The two submitted review forms agreed on 47 of 60 cases (78.33%), with unweighted nominal Cohen's kappa of 0.4433. There were 13 disagreements.

Both submissions disclosed AI assistance. The recorded provenance describes one adopted AI-assisted reviewer-1 draft and one AI-assisted reviewer-2 submission confirmed by the reviewer. The result must be described as agreement between submitted forms, not as two fully independent, unaided human annotations. The stratified panel is diagnostic and does not estimate dataset-wide label accuracy or prevalence.

## 7.2 Adjudication and tracker comparison

The 13 disagreements were finalized in a separate adjudication record before the tracker key was opened. The final decisions were 10 unresolved, two grow, and one shrink. Combining these with the 47 initial matches yields the final 60-case panel.

The final panel matches the frozen tracker on 26 of 60 cases (43.33%) and differs on 34. The principal discrepancy is review-unresolved versus tracker-dissolve (24 cases). Other differences are review-unresolved versus tracker-grow (5), review-unresolved versus tracker-merge (1), review-grow versus tracker-unresolved (2), review-merge versus tracker-unresolved (1), and review-shrink versus tracker-unresolved (1).

These are differences between a review interpretation of supplied evidence and an operational tracker rule. They do not prove that the tracker is wrong, that the social group disappeared, or that the corpus has a collection defect. The panel is stratified and cannot be generalized to the full dataset.

## 7.3 Source-lineage audit

Across all 60 focal communities, lineage status is: 52 with no accepted predecessor, five with an ambiguous lineage reset, and three with unique continuation. Among the 13 adjudicated cases, the counts are nine with no accepted predecessor, two ambiguous resets, and two unique continuations.

In 43 cases, the lineage flag indicates no accepted predecessor while member-activity history is available. These are different feature channels and must not be conflated. The source-month audit reconstructed accepted incoming links from the pinned inclusion table and checked the saved age and history semantics against the frozen feature records. The graph audit of the 13 disputed cases marked four checks confirmed and nine not confirmed. “Not confirmed” means that the supplied evidence was insufficient to confirm the specified relationship; it does not establish that the event is false or that the pipeline is defective.

The audit covers the saved source-month lineage semantics and previously audited ages. It is not a complete reconstruction of raw graphs or a proof of all identity mappings and corpus/filter completeness.

## 7.4 Separate six-case automated supplement

A separate six-case assessment was completed using an automated assistant assessment. Its recorded outcomes were three unresolved, one grow, one shrink, and one observed-network dissolve, all at medium confidence. Human decisions for these six cases remain unrecorded. These cases do not enter the 60-case agreement calculation, adjudication count, or 26/60 tracker comparison. They must remain a separately identified exploratory supplement.

# 8. Ablation Study: H1 HeTCo 2015 Pilot

## 8.1 Scope and objective

H1 tests the declared hypothesis that selecting only the dissolve-versus-event decision threshold on inner origins would increase event recall in lineage-overlap conditions without increasing false events. This experiment concerns the separate 2015 HeTCo pilot, not the full-study 2018 cohort. The pilot has 571 main-window samples per seed.

The experiment retains HeTCo v4 as the pilot primary and reports HeTCo v5 as a threshold ablation. The full-study primary `hier_lr_dynamic` remains unchanged.

## 8.2 V4/V5 setup

The model uses a hierarchical head, balanced class weights, extended member attributes, HeTCo hidden size 8, 300 epochs, learning rate 0.01, and L2 0.001. The threshold grid is argmax, 0.3, 0.4, 0.5, 0.6, and 0.7. Selection uses label months July–September 2015, with the main evaluation beginning in October 2015. Each origin trains only on earlier label months.

The frozen schedule contains 27 selection fits and 63 evaluation fits, for 90 measured fits in total. Seeds are 42, 43, and 44. Threshold candidates reuse the same fitted probabilities; they do not require additional estimator fits. The selected attention threshold is 0.3, while mean pooling and community-only hierarchical LR retain argmax.

## 8.3 Results and adverse mechanism

| Family / decision | Main Macro-F1 | Rolling Macro-F1 |
|---|---:|---:|
| HeTCo v4 attention, argmax (pilot primary) | 0.3976 | 0.3924 |
| HeTCo v5 attention, threshold 0.3 | 0.4109 | 0.3967 |
| Mean pooling control | 0.3490 | 0.3750 |
| Community-only hierarchical LR control | 0.3974 | 0.3812 |

The main-window Macro-F1 difference for v5 versus v4 is +0.0133. The saved community-bootstrap interval is [-0.0043, 0.0279], which includes zero. The rolling difference is +0.0043, with month-block interval [-0.0141, 0.0131], also including zero.

The aggregate gain does not support the mechanism predicted by H1. Mean missed events increase from 18 to 22 per seed, while false events decrease from 46.7 to 26.0. In the predeclared overlap stratum, tier-1 event recall decreases from 0.651 to 0.508. Thus v5 reduces false events but misses more true events, including in the stratum where H1 predicted a recall improvement.

The 5–20 size stratum is extremely small (n=59 in the pilot), and the >20 stratum contains 25 cases. Stratum-level changes should be interpreted cautiously. Main and rolling windows overlap, and the rolling July–September period also overlaps threshold selection. The rolling result is therefore descriptive and optimistic for selection, not unseen confirmation.

## 8.4 H1 conclusion

**H1 is not supported in its predicted direction.** The small Macro-F1 increase is uncertain, missed-event counts increase, and tier-1 event recall decreases in the overlap stratum. HeTCo v4 remains the pilot primary; v5 is retained as an adverse-mechanism ablation. The 2015 pilot results must not be combined with the full-study 2018 comparison table.

# 9. Limitations and Discussion

Several limitations constrain interpretation:

1. **Operational labels:** Event labels depend on graph construction, community detection, and tracker thresholds. They are not direct observations of social identity.
2. **Incomplete label resolution:** Community-month coverage is 64.78%; unresolved and censored cases are outside predictive metrics.
3. **Class imbalance:** Dissolve accounts for 91.96% of the final 2018 evaluation cohort. Stable has only four cases, grow 19, and merge 15.
4. **Retrospective evaluation window:** The January–September 2018 cohort was previously inspected during exploratory stages. It is a retrospective development/replication cohort, not an unseen prospective test set.
5. **No full resolved-population prediction export:** The final predictions cover 1,269 cases, not all 7,490 resolved records.
6. **Subgroup support:** Some size/history strata are small or lack event classes. Fixed-six-class Macro-F1 can be low when classes are absent.
7. **Descriptive coverage analysis:** A3 does not include formal effect sizes or inferential tests. Distribution differences do not establish why labels are unresolved.
8. **Paired comparison interpretation:** Macro-F1 and paired correctness weight observations differently. A model can have higher Macro-F1 but fewer individually correct cases.
9. **Seed dependence:** Repeated seeds use the same cases and are not independent observations.
10. **Human-review provenance:** The 60-case submissions disclosed AI assistance. The panel is diagnostic and stratified, not a representative sample of all labels.
11. **Graph-audit scope:** The lineage and graph checks verify supplied saved evidence within a limited scope, not the complete raw corpus or every identity mapping.
12. **H1 pilot boundary:** H1 uses a separate 2015 pilot, different references, and an overlapping rolling/selection window. It cannot confirm full-study generalization.

The most defensible interpretation is that the study has a clear applicability boundary, a strong majority-class signal, and substantial uncertainty for rare structural events. The proposed full-study model improves Macro-F1 over the principal HGB comparator but does not win the paired correctness comparison. The H1 threshold change has not demonstrated the intended event-recall mechanism.

# 10. Conclusion

This integrated analysis combines label coverage, predictive evaluation, error diagnostics, reviewer agreement, tracker comparison, lineage verification, Week 4 paired model comparison, and a separately scoped H1 pilot.

The full-study community-month label coverage is 64.78%, with 7,490 resolved, 4,072 unresolved, and 183 terminally censored records. The final 2018 prediction cohort contains 1,269 resolved cases and is highly imbalanced. `hier_lr_dynamic` achieves Macro-F1 0.4117, compared with 0.3880 for `hier_hgb_dynamic`, but the paired comparison yields 29 proposed-only correct versus 35 HGB-only correct cases. Weak grow, merge, and stable recall remains a central limitation.

The 60-case review panel shows 78.33% agreement between submitted forms (kappa 0.4433), followed by 13 adjudications and 26/60 matches with the frozen tracker. AI-assistance provenance and stratified sampling limit the scope of this evidence. The separate six-case automated supplement is not human review. The source-lineage audit distinguishes predecessor status from member-activity history.

Finally, the separate 2015 H1 pilot does not support its predicted mechanism. Although v5 raises Macro-F1 slightly, it increases missed events and reduces event recall in the overlap stratum. HeTCo v4 therefore remains the pilot primary, while the full-study `hier_lr_dynamic` primary remains unchanged.

Future work should prioritize better resolution and independent validation of ambiguous transitions, improved discrimination of grow and merge from dissolve, and prospective evaluation on genuinely unseen time periods. Any future model change should be assessed on matched cases and reported with both class-balanced metrics and paired correctness outcomes.

---

# Claim–Evidence Table

| ID | Claim | Evidence | Source location | Status / qualification |
|---|---|---|---|---|
| C01 | Community-month label coverage is 64.78%. | 7,490 resolved / (7,490 + 4,072 unresolved). | `reports/tables/midterm2-20261104/B/tables/` and `reports/MIDTERM2_DIAGNOSTIC_REPORT.md` §4 | Verified; censored 183 reported separately. |
| C02 | Member-month weighted coverage is 79.31%. | 1,417,626 / 1,787,503. | `reports/MIDTERM2_DIAGNOSTIC_REPORT.md` §4.1 | Verified; different denominator/weighting from C01. |
| C03 | Coverage varies by size and history. | `B_size_coverage.csv`, `B_history_coverage.csv`. | `reports/tables/midterm2-20261104/B/tables/` | Verified; descriptive only. |
| C04 | The proposed model has the highest Macro-F1 among primary full-study reference models. | `hier_lr_dynamic` 0.4117 vs `hier_hgb_dynamic` 0.3880 and listed baselines. | `A1_overall_macro_summary.csv`; Week 4 `primary_baseline_comparison.csv` | Verified; does not imply most paired correct cases. |
| C05 | Accuracy alone is misleading under severe class imbalance. | Dissolve = 1,167/1,269 (91.96%); majority baseline accuracy 0.9196 but Macro-F1 0.1597. | A1 summary; Week 4 report §1 | Verified. |
| C06 | Proposed-model recall is weak for grow and merge. | Grow recall 0.1579 (n=19); merge recall 0.2000 (n=15). | `A1_overall_class_metrics.csv`; Week 4 `per_class_metrics.csv` | Verified; rare-class support is small. |
| C07 | Monthly Macro-F1 varies across 2018. | `A1_monthly_macro_summary.csv`; proposed monthly values 0.2445–0.5496. | `reports/tables/midterm2-20261104/A1/tables/` | Verified; descriptive, not a temporal trend. |
| C08 | Performance differs across size/history strata. | `A2_stratified_macro_summary.csv`; `A2_size_macro_summary.csv`. | `reports/tables/midterm2-20261104/A2/tables/` | Verified; interpret with stratum support and class mix. |
| C09 | Resolved and unresolved records differ in size means but share median size 2. | Resolved mean 189.27 vs unresolved 90.83; median 2 for both. | `A3_numeric_comparison.csv` | Verified; highly skewed distributions; no inferential tests. |
| C10 | The dominant proposed-model errors include dissolve→grow and grow→dissolve. | Counts 37 and 14; plus split→shrink 12. | `error_analysis/tables/misclassification_pairs.csv` | Verified for seed 42. |
| C11 | Proposed has higher Macro-F1 than HGB. | 0.4117 vs 0.3880. | Week 4 `primary_baseline_comparison.csv` | Verified. |
| C12 | Proposed has fewer paired correct cases than HGB. | 29 proposed-only wins vs 35 HGB-only losses; net -6. | Week 4 `paired_wins_losses_summary.csv` | Verified; identical counts across seeds. |
| C13 | Reviewer submissions agree on 47/60 cases. | 78.33% raw agreement; kappa 0.4433. | `REPORT_FOR_ANH.md`; `01_agreement_adjudication/summary.json` | Verified; both submissions disclosed AI assistance. |
| C14 | The 13 disagreements were adjudicated as 10 unresolved, 2 grow, 1 shrink. | Final adjudication counts. | `01_agreement_adjudication/summary.json`; `adjudication.csv` | Verified. |
| C15 | Final review matches tracker on 26/60 cases. | 26 matches, 34 mismatches. | `02_tracker_audit/summary.json`; `confusion_review_vs_tracker.csv` | Verified; stratified diagnostic panel only. |
| C16 | Most tracker disagreements are review-unresolved vs tracker-dissolve. | 24 cases. | `02_tracker_audit/summary.json`; `confusion_review_vs_tracker.csv` | Verified; does not prove tracker error or social disappearance. |
| C17 | Lineage status in 60 cases is 52 no predecessor, 5 ambiguous reset, 3 unique continuation. | Reconstructed source-month lineage audit. | `02_tracker_audit/summary.json`; `lineage_by_scope.csv` | Verified within saved audit scope. |
| C18 | No accepted predecessor and member-activity history are distinct. | 43 cases have no accepted predecessor but activity history available. | `REPORT_FOR_ANH.md`; `02_tracker_audit/summary.json` | Verified; do not conflate feature channels. |
| C19 | The six-case supplement is not human review. | Automated assistant assessment; human decisions unrecorded. | `reports/MIDTERM2_DIAGNOSTIC_REPORT.md` §9; supplementary summary | Verified; exclude from reviewer agreement/tracker panel. |
| C20 | H1 is not supported in its predicted direction. | v5 main Macro-F1 +0.0133 but missed events 18→22; overlap tier-1 recall 0.651→0.508; paired interval includes zero. | `reports/H1_ABLATION_REPORT.md`; `ablation.csv`; `saved-intervals.json`; notebook `08_h1_ablation.ipynb` | Verified; separate 2015 pilot only. |
| C21 | HeTCo v4 remains the H1 pilot primary; v5 is an adverse-mechanism ablation. | H1 verification record and report decision. | `reports/H1_ABLATION_REPORT.md`; `verification.json` | Verified; does not change full-study primary. |
| C22 | The full-study evaluation is not an unseen prospective test. | 2018 final horizon previously inspected during exploratory stages. | Week 4 report §7 | Verified limitation. |

---

# Evidence inventory for the combined report

## Full-study diagnostics (main repository)

- `reports/MIDTERM2_DIAGNOSTIC_REPORT.md`
- `reports/tables/midterm2-20261104/README.md`
- `reports/tables/midterm2-20261104/A1/tables/A1_overall_macro_summary.csv`
- `reports/tables/midterm2-20261104/A1/tables/A1_overall_class_metrics.csv`
- `reports/tables/midterm2-20261104/A1/tables/A1_monthly_macro_summary.csv`
- `reports/tables/midterm2-20261104/A1/tables/A1_overall_confusion.csv`
- `reports/tables/midterm2-20261104/A2/tables/A2_stratified_macro_summary.csv`
- `reports/tables/midterm2-20261104/A2/tables/A2_size_macro_summary.csv`
- `reports/tables/midterm2-20261104/A3/tables/A3_numeric_comparison.csv`
- `reports/tables/midterm2-20261104/A3/tables/A3_status_by_size_band.csv`
- `reports/tables/midterm2-20261104/A3/tables/A3_status_by_history.csv`
- `reports/tables/midterm2-20261104/B/tables/B_monthly_coverage.csv`
- `reports/tables/midterm2-20261104/B/tables/B_size_coverage.csv`
- `reports/tables/midterm2-20261104/B/tables/B_history_coverage.csv`
- `reports/tables/midterm2-20261104/error_analysis/tables/error_by_true_class.csv`
- `reports/tables/midterm2-20261104/error_analysis/tables/misclassification_pairs.csv`

## Week 4 comparison (main repository)

- `reports/WEEK4_COMPARISON_REPORT.md`
- `reports/tables/week4-comparison-20261111/primary_baseline_comparison.csv`
- `reports/tables/week4-comparison-20261111/per_class_metrics.csv`
- `reports/tables/week4-comparison-20261111/per_month_macro_f1.csv`
- `reports/tables/week4-comparison-20261111/paired_wins_losses_summary.csv`
- `reports/tables/week4-comparison-20261111/paired_wins_losses_by_class.csv`
- `reports/tables/week4-comparison-20261111/paired_wins_losses_by_month.csv`
- `reports/tables/week4-comparison-20261111/paired_cases_proposed_vs_hgb.csv`
- `reports/tables/week4-comparison-20261111/reconciliation_summary.json`
- `reports/tables/week4-comparison-20261111/target_cases_evaluation.json`

## Human review handoff (main repository)

- `reports/tables/human-review-20261107/01_agreement_adjudication/summary.json`
- `reports/tables/human-review-20261107/01_agreement_adjudication/adjudication.csv`
- `reports/tables/human-review-20261107/01_agreement_adjudication/confusion_7labels.csv`
- `reports/tables/human-review-20261107/02_tracker_audit/summary.json`
- `reports/tables/human-review-20261107/02_tracker_audit/confusion_review_vs_tracker.csv`
- `reports/tables/human-review-20261107/02_tracker_audit/lineage_by_scope.csv`
- `reports/tables/human-review-20261107/03_graph_evidence/graph_lineage_check.csv`

## H1 pilot (main repository)

- `reports/H1_ABLATION_REPORT.md`
- `notebooks/core/08_h1_ablation.ipynb`
- `reports/tables/h1-ablation-20261109/ablation.csv`
- `reports/tables/h1-ablation-20261109/contrasts.csv`
- `reports/tables/h1-ablation-20261109/per-class.csv`
- `reports/tables/h1-ablation-20261109/main-strata.csv`
- `reports/tables/h1-ablation-20261109/saved-intervals.json`
- `reports/tables/h1-ablation-20261109/verification.json`
- `reports/tables/h1-ablation-20261109/fit-log.csv`
