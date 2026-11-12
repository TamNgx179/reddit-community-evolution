# Integrated Midterm 2 Report
## Forecasting Structural Events in Reddit User Communities

**Reporting scope:** Full-study diagnostics, Week 4 model comparison, human review and tracker audit, and the separate H1 HeTCo pilot  
**Evidence cutoff:** 11 November 2026  
**Primary full-study model:** `hier_lr_dynamic`

> **Study-boundary note.** The full-study evaluation (1,269 community-month samples from January–September 2018) and the H1 HeTCo pilot (571 main-window samples from 2015) are separate studies with different reference labels and protocols. Their scores must not be pooled or placed in one model-ranking table. H1 does not replace or modify the full-study primary model.

---

# Abstract

We study whether structural changes in Reddit user communities can be forecast from monthly reply networks. Communities are detected with weighted Leiden and linked across months by a GED adaptation. Of 11,562 observed transitions, 7,490 receive a resolved label. On 1,269 chronological evaluation cases, hierarchical logistic regression reaches six-class Macro-F1 of 0.4117 versus 0.3880 for hierarchical gradient boosting. The paired month-block interval for the difference includes zero, and boosting correctly predicts six more cases per seed. A stratified review panel exposes disagreements between tracker-assigned dissolution and unresolved transitions. A diagnostic threshold probe reduces missed grow and merge predictions at the cost of more false event alarms. These results locate the applicability boundary and motivate independent label review and targeted forecasting checks.

## Key findings

- **Applicability.** The frozen tracker resolves 64.78% of observed transitions. Lowering the dissolve threshold removes 68 originally scored cases. Macro-F1 increases on the remaining cases with identical predictions and labels.
- **Partition sensitivity.** Alternative Leiden seeds preserve 1,805 of 1,808 aligned labels per comparison on the final nine months. A further 24 source groups per comparison have no qualifying match.
- **Forecasting.** The proposed model scores 0.4117 versus 0.3880 Macro-F1 for hierarchical HGB. The paired interval includes zero and HGB correctly predicts six more cases per seed.

# 1. Introduction and Research Questions

Online communities change over time as members join, leave, interact, and reorganize. This study examines whether structural events in detected online communities can be predicted from information available before the next monthly transition.

The prediction task uses six event classes: **stable, grow, shrink, merge, split, and dissolve**. The operational target is defined by the observed interaction graph, community detection, and the declared lineage/event-tracking rules. It should therefore be interpreted as a rule-based structural event label, rather than an unquestionable statement about the social identity or continued existence of a group.

The technical input is a detected community at month *t* and its graph, activity and history features observed through that month. The output is a six-class probability distribution and an event prediction for *t → t+1*. The study connects community evolution to forecasting by treating the monthly detected groups as the units to track.

The integrated analysis addresses four questions:

1. **Label applicability:** What proportion of observed community-month transitions receives a resolved event label, and how do resolved, unresolved, and terminally censored records differ?
2. **Predictive performance:** How does the proposed hierarchical logistic-regression model perform across the six classes, calendar months, community sizes, and history-availability strata?
3. **Comparative performance:** Does the proposed model outperform the hierarchical HGB comparator and matched controls on the same frozen evaluation cases, and where does it make different errors?
4. **Label interpretation and hypothesis testing:** How closely do submitted reviewer decisions agree with one another and with the frozen tracker, and does the separate H1 threshold ablation support its predicted mechanism?

The evidence is descriptive and comparative. It does not establish causal effects of features, universal superiority, or prospective performance on unseen future data.

# 2. Dataset and Graph Construction

The full study uses 15 ConvoKit Reddit corpora and 45 monthly snapshots from January 2015 through September 2018. Each subreddit supplies an activity context. Detected communities consist of users who interact in the monthly reply network. Valid replies are represented as directed author-to-parent-author interactions, assigned to the UTC month of the child record. The undirected user projection aggregates reply counts in both directions.

Communities are detected independently in each monthly snapshot using weighted Leiden partitions. The declared GED adaptation compares member overlap and importance-weighted inclusion to establish transition links and community events. A directional inclusion of at least 0.5 accepts a lineage link. The declared dissolution threshold is 0.1; competing weak or ambiguous patterns can remain unresolved.

The prediction unit is a detected community at month *t*. Features are restricted to records available through *t*, while the target describes the transition from *t* to *t+1*. This cutoff is essential: later information must not be used to construct predictors for an earlier prediction point.

The pipeline follows one sequence:

1. Read posts and comments with their author, timestamp and parent record. Resolve each valid reply to a parent author.
2. Assign each reply to the child record’s UTC month. Aggregate directed reply counts into an undirected weighted user graph for Leiden.
3. Detect communities independently each month. For each adjacent pair of months, compare membership and importance overlap in both directions.
4. Build features through month *t*, then join them to the structural label for *t → t+1*. Compare saved predictions using the same reference, community and target month.

The resulting labels are operational outputs of the graph construction, community detection, and tracking rules. A tracker-assigned dissolve label means that the declared continuity procedure did not accept a successor under its rules; it does not independently prove that the underlying social group disappeared.

# 3. Labeling and Coverage

The GED adaptation accepts a successor when either directional inclusion reaches its threshold of 0.5. With one accepted successor and one predecessor, the relative sizes determine grow, shrink or stable. Multiple accepted successors indicate split and multiple predecessors into a single accepted successor indicate merge. A many-to-many pattern is unresolved. With no accepted successor, the tracker records dissolve when every directional inclusion is below 0.1. Weaker overlap at or above 0.1 leaves the event unresolved. The final observed month has no target snapshot and is censored.

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

## 3.5 Two graph cases from the diagnostic review

| Case | Evidence across the two snapshots | Recorded adjudication |
|---|---|---|
| `main-0010` | All four focal users appear in a target of 16,293 members. Focal edges drop from three to one, and the largest retained focal component has two users. | **Unresolved.** Shared membership in a large target gives limited evidence that the focal group merged as a coherent unit. |
| `main-0012` | The target grows from 82 to 114 users. It retains 25 focal users, including a connected core of 23, with 25 prior edges persisting. | **Grow.** The connected retained core supports a dominant continuation. Retention of 25/82 and incomplete observation qualify the decision. |

These examples come from the diagnostic review panel. The recorded decisions are the panel's adjudications and remain separate from the frozen prediction targets. See the [case audit](tables/human-review-20261107/03_graph_evidence/graph_lineage_check.csv) and [adjudication records](tables/human-review-20261107/01_agreement_adjudication/adjudication.csv).

The full-study coverage and monthly graph consistency were independently replayed from the frozen inputs. All 45 monthly manifests matched the sample run, and the graph audit checked membership, edge endpoints and observation denominators. This check establishes the consistency of the supplied graph artifacts. See [the coverage and graph audit](https://github.com/TamNgx179/reddit-community-evolution/blob/afec18c/docs/PHUC-WEEK4-RESULTS.md).

## 3.6 Sensitivity to GED thresholds

The threshold replay reproduced all 11,745 frozen labels before changing one parameter at a time. Moving the linkage threshold from 0.50 to 0.45 or 0.55 changed 15 or 63 labels. With linkage fixed, moving the dissolve threshold from 0.10 to 0.05 reassigned 623 dissolve cases to unresolved and reduced coverage from 64.78% to 59.39%. Moving it to 0.15 reassigned 352 unresolved cases to dissolve and raised coverage to 67.83%. The graph and partitions were held fixed. This quantifies how the operational definition changes eligibility and motivates review of ambiguous and weakly observed cases. The reported forecasting scores use the original frozen labels. [Sensitivity table](tables/sna-feedback-20261111/ged_threshold_sensitivity.csv) and [transition counts](tables/sna-feedback-20261111/ged_threshold_transitions.csv).

## 3.7 Separating eligibility changes from label changes

We rescored the saved predictions on the intersection of the original final prediction keys and cases resolved under each alternate GED rule. We first restricted the original labels to those keys, then substituted the alternate labels on the same keys. These two steps separate the effect of sample eligibility from the effect of relabeling. The replay uses fixed predictions and six-class Macro-F1 averaged over the three frozen seeds.

At dissolve threshold 0.05, 68 of the original 1,269 final cases leave the scored set. The other 1,201 retain their original labels. The proposed model moves from 0.4117 to 0.4136 and hierarchical HGB from 0.3880 to 0.3912 entirely through the change in eligibility. At linkage threshold 0.55, seven cases leave the scored set and four retained cases change label. For the proposed model, the eligibility step moves the score from 0.4117 to 0.3957, and the relabeling step moves it to 0.4006. The proposed score is higher than HGB in all five inspected settings on their respective common keys. These are point estimates on a previously inspected cohort. The replay cannot score newly eligible cases without corresponding saved predictions. [Matched eligibility and label sensitivity](tables/sna-feedback-20261111/ged_frozen_prediction_sensitivity.csv).

## 3.8 Sensitivity to the Leiden partition seed

We held the monthly reply graphs, Leiden objective and resolution, and GED thresholds fixed. We replayed GED with saved Leiden partitions for seeds 0, 1 and 2, recomputing within-community importance for each partition. Seed 0 exactly reproduced the frozen labels for **1,832** source groups over the nine final target months (January–September 2018), including unresolved groups. We aligned source groups within each month using a unique reciprocal best membership Jaccard match of at least 0.50.

| Alternative seed | Seed-0 source groups | Aligned | Same label | Different label | Unmatched |
|---|---:|---:|---:|---:|---:|
| 1 | 1,832 | 1,808 | 1,805 | 3 | 24 |
| 2 | 1,832 | 1,808 | 1,805 | 3 | 24 |

The concordance among aligned groups is 99.83% for each comparison. No aligned case moved directly between dissolve and unresolved. Some original dissolve and unresolved groups failed the alignment threshold, so the matched result applies to comparable groups in these snapshots. This analysis varies the partition seed at fixed graph construction and GED settings. Section 3.6 varies GED thresholds at fixed partitions. Together the checks locate sensitivity under the tested perturbations. [Monthly audit](tables/sna-feedback-20261111/leiden_seed_monthly.csv), [label transitions](tables/sna-feedback-20261111/leiden_seed_label_transitions.csv) and [label-specific denominators](tables/sna-feedback-20261111/leiden_seed_label_denominators.csv).

# 4. Evaluation Protocol

The full-study predictive evaluation uses the frozen final prediction window from January through September 2018. It contains **1,269 unique community-month cases per seed**, **19 model configurations**, and seeds **42, 43, and 44**.

The evaluation uses a fixed six-class label set: stable, grow, shrink, merge, split, and dissolve. Macro-F1 is calculated across all six classes with `zero_division=0`. Unresolved and terminally censored records are excluded from predictive metrics; neither is converted into an event class.

The acceptance runner checked uniqueness, matched evaluation keys, label agreement and feature availability through month *t*. The full join uses graph reference, feature month, community ID, label month and label reference. The 1,269 evaluation cases are drawn from the 7,490 resolved records according to the frozen final window. This is an analysis of saved predictions. Fit cutoff is checked against the declared protocol for the frozen exports. The H1 run has its own fit log and verification record.

The three seeds are repeated runs on the same evaluation cases, not independent test samples. Identical results across seeds for deterministic configurations must not be interpreted as evidence of stability under new sampling conditions.

# 5. Baselines and Proposed Methods

The primary full-study method is `hier_lr_dynamic`, a hierarchical logistic-regression configuration with dynamic features. Its first head estimates dissolve versus other events. Its second head estimates the other event classes conditional on continuation. The final six-class probabilities combine those two estimates. The principal reference comparator, `hier_hgb_dynamic`, uses the same hierarchical decision structure with HGB estimators. This comparison tests estimator choice under the declared dynamic setup. Comparisons with flat LR and the controls address architecture and feature choices separately. Other reference baselines include majority prediction, persistence, random forest, logistic regression, and matched boosting. Additional controls isolate hierarchy, dynamics, context drift, and static/dynamic feature choices.

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

The proposed model gains 0.0237 Macro-F1 over hierarchical HGB. Sections 6.5 and 6.6 show how the per-case outcomes and month-block interval qualify that gain.

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

The proposed model achieves 0.4117 Macro-F1, compared with 0.3880 for hierarchical HGB. The matched 95% interval for their difference is **[−0.0694, +0.0945]**, which includes zero. The estimate comes from 1,000 paired bootstrap draws with blocks of two consecutive months over nine observed months. Each draw uses the same months for all models and seeds. This interval describes exploratory uncertainty within the inspected evaluation period.

| Comparator | Proposed minus comparator Macro-F1 | Paired 95% interval |
|---|---:|---:|
| Hierarchical HGB dynamic | +0.0237 | [−0.0694, +0.0945] |
| Flat HGB dynamic | +0.0476 | [−0.0303, +0.1163] |
| Flat LR dynamic | +0.0502 | [−0.0294, +0.1176] |
| B4 Logistic Regression | +0.0806 | [−0.0101, +0.1418] |
| B5 Matched Boosting | +0.1788 | [+0.0843, +0.2524] |

The saved matched controls help interpret the model comparison. The no-dynamics contrast yields **+0.0474** Macro-F1 with a paired interval of **[−0.0073, +0.0934]**. The flat matched contrast yields **+0.0796** with an interval of **[+0.0292, +0.1321]**. These estimates describe their respective frozen configurations and the inspected period.

The paired correctness counts favor HGB by six cases per seed. Among the 19 grow cases, the proposed model predicts dissolve 14 times and HGB 12 times. Among the 15 merge cases, the counts are 8 and 9. The direction differs by class, and the small supports limit interpretation. The proposed method's benefit is higher class-balanced performance on this window. Whether that benefit persists across new months remains an open question.

## 6.7 Retrospective decision-rule probe

On the 1,269 previously inspected final cases, retain the frozen scores and change a dissolve argmax only when its probability is below 0.5. In that case, select the highest-scoring remaining event. This isolates the decision rule while holding training, features and scores fixed.

| Seed 42 decision | Grow correct / 19 | Merge correct / 15 | Grow or merge called dissolve | False event alarms / 1,167 dissolve | Macro-F1 |
|---|---:|---:|---:|---:|---:|
| Proposed argmax | 3 | 3 | 22 | 64 | 0.4117 |
| Hierarchical HGB | 3 | 3 | 21 | 55 | 0.3880 |
| Proposed with 0.5 dissolve rule | 6 | 5 | 13 | 134 | 0.4130 |

The probe gains +0.0012 Macro-F1 over the original decision rule, with a paired month-block 95% interval of [−0.0288, +0.0423]. The additional 70 false alarms outweigh the evidence for adopting this rule. Retain the original full-study configuration.

Against the matched no-dynamics configuration, the proposed model gains +0.0569 Macro-F1 where member-activity history is available (730 cases) and changes by −0.0053 where it is missing (539 cases). Compared with the flat matched control, the hierarchical variant gains Macro-F1 in both strata but sends more grow and merge cases to dissolve. This distinction motivates a study of when dynamic signals help, with class support and false alarms reported jointly. The stratum results use seed 42 and are descriptive. See [matched strata](tables/sna-feedback-20261111/matched_strata_seed42.csv), [probe counts](tables/sna-feedback-20261111/gate_probe_seed42.csv), and [paired probe intervals](tables/sna-feedback-20261111/gate_probe_intervals.csv).

## 6.8 History-conditioned replay and month sensitivity

We replayed a conditional rule on the already inspected final window. It uses the saved dynamic prediction when member-activity history is available and the saved no-dynamics prediction otherwise. Both variants were evaluated on the same keys. This replay involves no new fits or threshold search. The rule was motivated by the descriptive differences in Section 6.7.

| Paired contrast | Cases per seed | Δ six-class Macro-F1 | Exploratory 95% month-block interval |
|---|---:|---:|---:|
| Dynamic vs. no-dynamics, history available | 730 | +0.0569 | [−0.0092, +0.1076] |
| Dynamic vs. no-dynamics, history missing | 539 | −0.0053 | [−0.0139, −0.0002] |
| Conditional replay vs. dynamic | 1,269 | +0.0018 | [−0.00008, +0.0027] |
| Conditional replay vs. hierarchical HGB | 1,269 | +0.0255 | [−0.0690, +0.0955] |

The replay moves Macro-F1 from 0.4117 to 0.4136 and reduces false event alarms among true dissolve cases from 64 to 60 at seed 42. Grow and merge hits remain three each, and 22 of these cases are still predicted as dissolve. Omitting any one of the nine months leaves a positive point difference between the replay and the existing proposed model (+0.0006 to +0.0027). This sensitivity check uses the same inspected cohort, and the paired interval for the overall improvement includes zero. The condition is a candidate for a future matched evaluation. The current proposed model remains the primary result.

To test whether the dynamic-feature gain differs between the two history strata, we computed the difference between their matched gains using the same sampled calendar months for both strata in each draw. The observed difference was **+0.0622 Macro-F1**. The 95% interval was **[−0.0099, +0.1123]** for two-month blocks and **[−0.0137, +0.1151]** for three-month blocks (2,000 draws each). Both intervals include zero. History availability is a plausible condition for further testing, and this retrospective window leaves the difference uncertain. [Shared-month sensitivity results](tables/sna-feedback-20261111/history_interaction_sensitivity.csv).

See the [paired intervals](tables/sna-feedback-20261111/history_conditional_intervals.csv), [decision counts](tables/sna-feedback-20261111/history_conditional_seed42.csv), and [leave-one-month-out results](tables/sna-feedback-20261111/history_leave_one_month_out.csv).

## 6.9 External-corpus replication of the conditional rule

We specified the conditional rule, comparators and adoption criteria before replaying the saved predictions from AustralianPolitics, CanadaPolitics and ukpolitics. The run covers 286 cases per seed over nine evaluation months. Prior team exposure is uncertified and users may overlap, so the scope is retrospective external-corpus replication. The replay checked feature cutoff, frozen input hashes and matching sample keys against the label export.

At seed 42, Macro-F1 is **0.3673** for the conditional rule, **0.3690** for the existing proposed model and **0.3500** for hierarchical HGB. The paired difference from the existing proposed model is **−0.0017**, with a two-month-block 95% interval of **[−0.0094, +0.0013]**. The three-month-block interval is **[−0.0111, +0.0012]**. False event alarms fall from 28 to 25 among 250 true dissolve cases at seed 42. Grow recall remains 0/8 and merge recall remains 2/9. The adoption criteria were not met, so the existing proposed model remains the primary configuration. [Replication protocol](tables/sna-feedback-20261111/external_history_replication_protocol.json) and [results](tables/sna-feedback-20261111/external_history_replication_results.json).

## 6.10 Does the LR–HGB advantage recur across corpora?

We replayed the named frozen dynamic LR and dynamic HGB models on common keys in each of three cohorts. The analysis rule was recorded before replaying these saved predictions. The two external comparisons are retrospective and team exposure is uncertified. Dynamic LR was a secondary comparison in the ideological cohort. We estimate each cohort separately.

| Cohort | Cases per seed | Δ Macro-F1, LR minus HGB | Paired 95% interval, two-month blocks |
|---|---:|---:|---:|
| Full-study | 1,269 | +0.0237 | [−0.0699, +0.0993] |
| External political | 286 | +0.0190 | [−0.2413, +0.2074] |
| External ideological | 493 | −0.0398 | [−0.0816, +0.0141] |

All intervals include zero with either two- or three-month blocks. At seed 42, LR produces more false event alarms among true dissolve cases on every cohort (64 vs. 55, 28 vs. 17, and 98 vs. 49). Combined grow/merge hits are respectively 6 vs. 6 of 34, 2 vs. 1 of 17, and 2 vs. 2 of 7. The point difference reverses on the ideological cohort, and the comparison fails the declared stability criterion. This supports keeping the current result scoped to the original cohort and retaining HGB as a strong comparator. [Replay protocol](tables/sna-feedback-20261111/lr_hgb_cross_cohort_protocol.json), [intervals](tables/sna-feedback-20261111/lr_hgb_cross_cohort_intervals.csv), and [decision counts](tables/sna-feedback-20261111/lr_hgb_cross_cohort_counts.csv).

### What drives the reversal?

We decomposed the Macro-F1 difference into the six class F1 differences divided by six and checked that the contributions sum to the reported difference for each cohort and seed. At seed 42, merge (+0.0196) and split (+0.0138) account for the positive full-study point difference. In the ideological cohort, grow (−0.0316) and dissolve (−0.0097) contribute most to the reversal. Both models correctly identify the same two grow cases out of seven there. Their different grow F1 comes from precision. There are zero true merge cases in this cohort. Among its 442 dissolve cases, HGB alone is correct on 63 and LR alone on 14.

These results suggest that the next candidate should address excess event predictions among true dissolve cases while tracking grow and merge recall on a cohort with support for both. Keep the frozen models as baselines. Predeclare the candidate, evaluation scope and acceptable false-alarm and recall tradeoff before testing. [Per-class contributions and paired correctness](tables/sna-feedback-20261111/lr_hgb_class_contributions.csv).

## 6.11 Validation-selected dissolve decision rule

We tested a single family of changes to address excess event predictions. A non-dissolve prediction switches to dissolve when the dissolve probability is at least a fixed fraction of the winning event probability. We refitted the frozen LR configuration at six pre-2018 validation origins, training only on earlier labels. The selection considered four ratios plus the original decision rule, and required fewer false alarms and no loss of correct grow or merge predictions at every seed. Among qualifying ratios, we selected the highest mean validation Macro-F1. This gave a ratio of **0.80** after **18 fits**. Across the 926 validation cases per seed, seed 42 false alarms fell from 52 to 37, grow and merge hits stayed at two each, and Macro-F1 rose from 0.4350 to 0.4442.

We applied the locked ratio to the existing model probabilities in the three previously inspected cohorts. The thresholds were selected on development data, while the following replay remains retrospective.

| Cohort | LR Macro-F1, original → rule | False alarms, original → rule | Grow hits | Merge hits |
|---|---:|---:|---:|---:|
| Full-study | 0.4117 → 0.3835 | 64 → 47 | 3 → 1 of 19 | 3 → 1 of 15 |
| External political | 0.3690 → 0.3814 | 28 → 21 | 0 → 0 of 8 | 2 → 2 of 9 |
| External ideological | 0.3646 → 0.3708 | 98 → 71 | 2 → 2 of 7 | No support |

Counts are for seed 42. The full-study paired Macro-F1 difference is **−0.0283**, with a two-month-block 95% interval of **[−0.0759, +0.0088]**. The rule reduces false alarms in each cohort but loses grow and merge hits on the full study. Its development improvement therefore does not satisfy the intended tradeoff across cohorts. We retain the original decision rule for the primary report. [Selection protocol](tables/sna-feedback-20261111/dissolve_guard_protocol.json), [validation trials](tables/sna-feedback-20261111/dissolve_guard_selection.json), [cohort counts](tables/sna-feedback-20261111/dissolve_guard_counts.csv), and [paired intervals](tables/sna-feedback-20261111/dissolve_guard_intervals.csv).

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

## 7.5 Blinded automated review on 12 development cases

Two agents separately applied the same rubric to identical blinded evidence drawn from four development months. The coordinator compared the completed outputs with the frozen tracker after both runs. The agents agreed on 11 of 12 cases (91.7%, unweighted Cohen’s κ = 0.868). Neither agent matched a tracker label in this stratified panel.

All four tracker dissolve cases had zero observed focal members in the next month. Both agents marked them unresolved. In three tracker unresolved cases, both agents marked dissolve because they observed some focal members while internal focal edges disappeared. The two agents disagreed on one case with retained ties in two targets. One selected shrink based on a dominant continuation, while the other selected split. These differences motivate explicit rubric criteria for observation sufficiency and continuity. The panel documents disagreement between operational rules and automated interpretations. Human validation remains pending. See the [aggregate results](tables/sna-feedback-20261111/automated_label_review_summary.json) and [agent confusion matrix](tables/sna-feedback-20261111/automated_label_review_confusion.csv).

## 7.6 Single-reviewer check on 12 additional development cases

Tâm annotated the cases on behalf of Thanh, as reported by Tâm. The evidence shown during annotation omitted the tracker labels. The 12 annotations were locked by SHA-256 before comparison with the frozen label export. This is one human annotator's comparison with the tracker on a separate exploratory panel of small communities (4–20 members eligible for sampling, one case per source month).

| Tracker label | Human dissolve | Human split | Human merge | Total |
|---|---:|---:|---:|---:|
| Dissolve | 7 | 2 | 0 | 9 |
| Unresolved | 0 | 2 | 1 | 3 |

The annotator matched the tracker on **7/12 cases (58.3%)**. All four cases with zero observed focal reply endpoints in the next month were called dissolve by both. In four disagreements the annotator called split based on members dispersing across targets. The fifth was called merge after members entered a much larger target. The observed evidence in these cases contained no focal internal edges in the next month. These patterns separate three questions for a future rubric: whether the focal users were observable, whether they dispersed across targets, and whether a group retained interaction ties. Agreement on zero-observation cases documents a shared interpretation of the observed snapshots. The available data leave social disappearance undetermined. This selected panel gives a case-level comparison. Agreement between two independent human annotators remains unmeasured. [Aggregate and lock checksum](tables/sna-feedback-20261111/delegated_human_review_summary.json).

## 7.7 Additional blinded automated panel

Two separate AI sessions labeled the same 36 cases using only the rubric and neutral evidence supplied to each. The case set was previously used for calibration. The two outputs were checked and hash-locked before opening the tracker key for this comparison. The agents agreed on **34/36 cases (94.4%)**, with nominal Cohen’s κ = **0.882**. Their tracker concordance was **8/36** and **9/36**. The result describes agreement between automated readings from the same model family on a diagnostic sample. Human inter-rater reliability remains unmeasured. [Aggregate counts and lock checksum](tables/sna-feedback-20261111/automated_panel36_summary.json).

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

## Follow-up study design

The next evaluation can test the history-conditioned rule from Section 6.8 as a single candidate. Before examining confirmation predictions, record the cohort, exposure, reference, label version, two component models, the existing primary and HGB controls, splits, feature cutoff, seeds, and decision criteria. Use the same evaluation keys and six fixed classes for all models. Specify the accepted tradeoff between false event alarms and grow/merge recall before scoring. Treat the current replay as development evidence.

For label validation, use two separate human annotations with a locked rubric and concealed tracker outputs. Record review provenance and retain both forms before computing agreement and adjudicating. Reviewers who have seen the automated labels or tracker answers for these cases need a fresh panel.

## Additional label audit and college-admissions cohort

The two reviewers agreed on 15 of 20 cases (75%, Cohen’s κ = 0.563). According to the submitter, each reviewer chose their labels separately, and one reviewer forwarded the files. Prior exposure to tracker labels was not recorded. The submitted forms were hash-checked before comparison with the tracker. Reviewer A matched the tracker on 5 of 20 cases and reviewer B on 4 of 20. The panel was stratified to diagnose ambiguous transitions, so these counts describe the selected cases.

Of the 15 cases with a shared reviewer label, 13 differed from the tracker.

| Tracker label | Shared reviewer label | Cases |
|---|---|---:|
| dissolve | unresolved | 6 |
| unresolved | dissolve | 3 |
| grow | dissolve | 2 |
| merge | dissolve | 2 |

In case 004, the March 2016 reply graph shows two members connected by one edge. In April, one of the two authored content, neither appeared as a reply endpoint or partition member, and no successor community was observed.

| Evidence for the original pair | March 2016 | April 2016 |
|---|---:|---:|
| Internal reply edges | 1 | 0 |
| Members observed as authors | — | 1 |
| Members observed as reply endpoints | — | 0 |
| Members in a detected community | 2 | 0 |

The tracker assigned `dissolve` because its continuity rule accepted no successor. Both reviewers chose `unresolved` because the next reply graph did not show either member. One member’s authorship shows continued activity, while the absence of reply endpoints leaves the relationship unobserved. This example motivates an observation check for no-successor cases before interpreting them as structural dissolution.

We replayed one observation rule on the frozen snapshots. A below-threshold `dissolve` becomes `unresolved` when no original member appears as a reply endpoint in the next month. The development split moved 4,613 of 5,700 dissolve cases, reducing resolved coverage from 6,221/9,730 (63.94%) to 1,608/9,730 (16.53%). The evaluation split moved 1,019 of 1,167 dissolve cases, reducing coverage from 1,269/1,832 (69.27%) to 250/1,832 (13.65%). The coverage denominator excludes terminally censored transitions.

Using frozen predictions on the same 250 retained cases per seed, LR scored 0.4295 and HGB scored 0.4093 in six-class Macro-F1. Their gap was +0.0202, compared with +0.0237 on all 1,269 cases. This retrospective analysis holds retained labels and predictions fixed. Its score changes reflect the change in which cases count toward the metric. The large coverage loss supports reporting reply observability as a diagnostic alongside the original benchmark.

A narrower rule, motivated by case 004, additionally requires at least one original member to have authored content in the next month. It moved 133 development cases and 34 evaluation cases, leaving coverage at 62.57% and 67.41%, respectively. All 34 flagged evaluation cases lacked a tracker successor and had exactly one observed author from the original community. They occurred in all nine evaluation months, and 27 came from two-member communities.

On the same 1,235 retained evaluation cases per seed, LR scored 0.4130 and HGB scored 0.3892, a gap of +0.0237 (95% interval [−0.0719, +0.0994]). On the original 1,269 cases, the same paired bootstrap protocol gave a gap of +0.0237 (95% interval [−0.0699, +0.0993]). Both use 2,000 paired two-month-block resamples and frozen predictions. The narrower rule is a practical flag for cases with limited reply evidence. The 34-case audit verifies its structural trigger, and human validation of these cases remains open. [Aggregate audit and paired results](tables/sna-feedback-20261111/observability-audit.json)

To check transfer beyond the original cohort, we declared the Cornell and ApplyingToCollege corpora and fixed the LR and HGB feature sets and hyperparameters before acquisition. Both models were fitted on the same 564 earlier cases and locked before the evaluation targets were built. On 843 cases spanning January 2017 through September 2018, hierarchical LR scored 0.2508 Macro-F1 and hierarchical HGB scored 0.2413. The paired difference was +0.0095 (95% interval [−0.0273, +0.0511], 2,000 three-month-block resamples). The direction agrees with the +0.0237 difference on the main cohort. Each rare class had six cases, below the declared minimum of 19 grow and 15 merge cases. The result therefore leaves the size and reliability of the advantage uncertain.

The development-selected probability blend used 75% LR and 25% HGB. Its main-cohort Macro-F1 was 0.3955 versus 0.4117 for LR. At seed 42, false event alarms fell from 64 to 52 and correct grow predictions fell from three to two. We retained hierarchical LR for the main comparison.

### Where the two models disagree

On the 1,269 matched evaluation cases at seed 42, both models were correct on 1,119, LR alone on 29, HGB alone on 35, and neither on 86. LR led on five of nine evaluation months. Its largest monthly deficit was −0.2102 in March 2018, which included three grow and two merge cases. Its largest monthly lead was +0.1406 in September, which included two grow cases and no merge cases.

| Source community and transition | Frozen graph evidence | Tracker | LR | HGB |
|---|---|---|---|---|
| c68, June to July 2018 | Both original users appear in a target of 4,538. The original internal edge disappears. | merge | merge | dissolve |
| c52, December 2017 to January 2018 | Two of three original users appear in a target of 5,532. Both original internal edges disappear. | merge | dissolve | merge |

The tracker recorded multiple predecessors in both cases. These examples show disagreement against the operational target and the limited evidence available for persistence of the original group's interactions. The paired outcomes are in the [frozen prediction comparison](tables/week4-comparison-20261111/paired_cases_proposed_vs_hgb.csv).

In the development replay at seed 42, LR predicted dissolve for 24 true grow or merge cases. Its conditional head ranked the true event first in nine and ranked another event first in 15. A threshold change alone could therefore address only a subset of these errors. Removing member-history features from the conditional head gained one grow hit on development but lost one merge hit on the main evaluation while gaining one grow hit. Macro-F1 fell to 0.4069 on the main evaluation and also fell on both external cohorts. On the main evaluation, the matched dynamic-feature gain was +0.0569 for the 730 cases with activity history and −0.0053 for the 539 without it. The paired interval for the difference between those gains included zero.

### Matched review of the observation flag

[Aggregate review and external-cohort results](tables/sna-feedback-20261111/final-audit-summary.json)

The prepared review contains all 34 flagged evaluation cases and 34 controls sampled without replacement from cases with the same tracker label. Each control matches its flagged case on target month and exact source size. The packets use opaque case IDs and conceal the tracker labels and pair assignments. The review will compare the proportion of paired cases for which both reviewers choose unresolved and report reviewer disagreements. The rule and matching design were fixed before collection of the two review forms. The packet alone supplies no human validation result.

The two automated draft reviews both selected `unresolved` for all 68 cases. The paired comparison was 34/34 flagged cases and 34/34 controls, a difference of zero percentage points. Raw agreement was 68/68. Cohen's kappa was undefined because both drafts used one label.

Among controls, 31 had no observed focal activity in the next month and three showed only one original member in a target without a surviving focal edge. The rubric treats missing observation as unresolved and calls for affirmative evidence of structural loss before assigning dissolve. The control group therefore tested a narrow comparison within tracker-assigned dissolve cases. The rule identifies a specific observation pattern, and the automated labels gave the same result on both sides. The submitted confirmation forms identified the two draft files by checksum and left personal review and signature fields blank.

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
| C04 | The proposed model has the highest Macro-F1 among primary full-study reference models. | `hier_lr_dynamic` 0.4117 vs `hier_hgb_dynamic` 0.3880 and listed baselines. | `A1_overall_macro_summary.csv`; Week 4 `primary_baseline_comparison.csv` | Paired 95% interval [−0.0694, +0.0945]. HGB has six more correct cases per seed. |
| C05 | Accuracy alone is misleading under severe class imbalance. | Dissolve = 1,167/1,269 (91.96%); majority baseline accuracy 0.9196 but Macro-F1 0.1597. | A1 summary; Week 4 report §1 | Verified. |
| C06 | Proposed-model recall is weak for grow and merge. | Grow recall 0.1579 (n=19); merge recall 0.2000 (n=15). | `A1_overall_class_metrics.csv`; Week 4 `per_class_metrics.csv` | Verified; rare-class support is small. |
| C07 | Monthly Macro-F1 varies across 2018. | `A1_monthly_macro_summary.csv`; proposed monthly values 0.2445–0.5496. | `reports/tables/midterm2-20261104/A1/tables/` | Verified; descriptive, not a temporal trend. |
| C08 | Performance differs across size/history strata. | `A2_stratified_macro_summary.csv`; `A2_size_macro_summary.csv`. | `reports/tables/midterm2-20261104/A2/tables/` | Verified; interpret with stratum support and class mix. |
| C09 | Resolved and unresolved records differ in size means but share median size 2. | Resolved mean 189.27 vs unresolved 90.83; median 2 for both. | `A3_numeric_comparison.csv` | Verified; highly skewed distributions; no inferential tests. |
| C10 | The dominant proposed-model errors include dissolve→grow and grow→dissolve. | Counts 37 and 14; plus split→shrink 12. | `error_analysis/tables/misclassification_pairs.csv` | Verified for seed 42. |
| C11 | Proposed has higher Macro-F1 than HGB. | 0.4117 vs 0.3880. | Week 4 `primary_baseline_comparison.csv` | Verified. |
| C12 | Proposed has fewer paired correct cases than HGB. | 29 proposed-only wins vs 35 HGB-only losses; net -6. | Week 4 `paired_wins_losses_summary.csv` | Verified; identical counts across seeds. |
| C13 | Reviewer submissions agree on 47/60 cases. | 78.33% raw agreement; kappa 0.4433. | `reports/tables/human-review-20261107/01_agreement_adjudication/summary.json` | Verified; both submissions disclosed AI assistance. |
| C14 | The 13 disagreements were adjudicated as 10 unresolved, 2 grow, 1 shrink. | Final adjudication counts. | `01_agreement_adjudication/summary.json`; `adjudication.csv` | Verified. |
| C15 | Final review matches tracker on 26/60 cases. | 26 matches, 34 mismatches. | `02_tracker_audit/summary.json`; `confusion_review_vs_tracker.csv` | Verified; stratified diagnostic panel only. |
| C16 | Most tracker disagreements are review-unresolved vs tracker-dissolve. | 24 cases. | `02_tracker_audit/summary.json`; `confusion_review_vs_tracker.csv` | Verified; does not prove tracker error or social disappearance. |
| C17 | Lineage status in 60 cases is 52 no predecessor, 5 ambiguous reset, 3 unique continuation. | Reconstructed source-month lineage audit. | `02_tracker_audit/summary.json`; `lineage_by_scope.csv` | Verified within saved audit scope. |
| C18 | No accepted predecessor and member-activity history are distinct. | 43 cases have no accepted predecessor but activity history available. | `reports/tables/human-review-20261107/02_tracker_audit/summary.json` | Verified; do not conflate feature channels. |
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


# References and reproducibility

- CornellNLP, *Reddit Corpus by subreddit*. [Corpus documentation](https://convokit.cornell.edu/documentation/subreddit.html).
- J. P. Chang et al., “ConvoKit: A Toolkit for the Analysis of Conversations,” *SIGDIAL*, 2020. [Paper](https://www.cs.cornell.edu/~cristian/ConvoKit_Demo_Paper_files/convokit-demo-paper.pdf).
- J. Baumgartner et al., “The Pushshift Reddit Dataset,” *ICWSM*, 2020. [Paper](https://doi.org/10.1609/icwsm.v14i1.7347).
- V. A. Traag, L. Waltman, and N. J. van Eck, “From Louvain to Leiden: Guaranteeing Well-Connected Communities,” *Scientific Reports*, 2019. [Paper](https://doi.org/10.1038/s41598-019-41695-z).
- P. Bródka, S. Saganowski, and P. Kazienko, “GED: The Method for Group Evolution Discovery in Social Networks,” *Social Network Analysis and Mining*, 2013. [Paper](https://doi.org/10.1007/s13278-012-0058-8).

The [Week 4 handoff](../docs/WEEK4_HANDOFF.md) provides the frozen inputs, checksums and replay commands. The [executed notebook](../notebooks/INTEGRATED_MIDTERM2_NOTEBOOK_20261111.ipynb) shows figures and outputs. For the paired interval, use `paired_tables` with 1,000 draws, block length 2 and bootstrap seed 20261031 on the full-study final predictions, normalizing the legacy window field to `final`.


# Appendix — Experimental plan and evidence

| Experiment | Question and design | Primary evidence |
|---|---|---|
| E1 Coverage | How much of the observed network has a resolved target? Count resolved and unresolved transitions by month, size and history. Count terminal censoring separately. Verify the frozen graph inventory. | Sections 2–3. |
| E2 Matched forecast | How do five reference baselines and the proposed model perform on the same 1,269 final cases? Report six-class Macro-F1, class support and paired monthly uncertainty. | Sections 4–6. |
| E3 Components | What changes when hierarchy or dynamic features are removed? Compare frozen matched variants. Inspect strata and adverse errors with their denominators. | Sections 6.5–6.7. |
| E4 Label audit | Which ambiguous cases need more evidence? Compare the two submitted forms, adjudication and graph traces. Compare a separate blinded automated panel and record the human validation status. | Section 7. The diagnostic panels and a separate one-annotator blind check are complete. Independent human inter-rater validation remains pending. |
| E5 H1 and decision-rule probe | Does a change in the dissolve decision recover target events? Report the 2015 pilot separately from the retrospective 2018 probe. Track false alarms alongside missed events. | Sections 6.7 and 8. |
| E6 Prototype | Can a teammate reproduce the reported scores? Verify the frozen bundle, replay metrics and inspect the executed notebook. | Week 4 handoff and reproducibility section. |
| E7 Observation sensitivity | Replay the observation flag on frozen graphs. Compare coverage and paired scores before and after filtering. Review 34 flagged cases and 34 controls matched by month and size. | Additional label audit and matched review. The automated comparison yielded 34/34 unresolved in both groups. |
| E8 External replication | Freeze LR and HGB before constructing evaluation labels. Compare the same 843 college-admissions cases across 21 months using paired month blocks. | College-admissions cohort results. The paired interval included zero and both rare classes fell below their declared support thresholds. |
