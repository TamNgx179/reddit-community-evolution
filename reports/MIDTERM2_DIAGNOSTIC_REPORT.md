# Week 3 — Community Evolution Diagnostic Report


This report records the completed Week 3 diagnostic work as of 9 November 2026. It integrates the frozen full-study evaluation, observation and label coverage, paired forecast errors, submitted review agreement, adjudication and post-lock tracker comparison.

### Problem, graph and operational target

The unit of analysis is a detected user community at month t. The task predicts its next-month structural event from six labels — stable, grow, shrink, merge, split and dissolve. Input features use records available through t. The target uses the transition from t to t+1. Unresolved transitions and terminally censored communities enter the applicability audit as separate statuses.

The original study uses 15 Reddit corpora and 45 monthly snapshots from January 2015 through September 2018. Valid replies create directed author-to-parent-author interactions in the child record's UTC month. The undirected user projection sums reply counts in both directions. Independent weighted Leiden partitions define the communities in each snapshot. The declared GED adaptation compares member overlap and importance-weighted inclusion to assign transition links and events. A directional inclusion of at least 0.5 accepts a link. The declared dissolution threshold is 0.1, and competing weak or ambiguous patterns can remain unresolved. Consequently the prediction target is defined jointly by the graph, detector and tracker.

Two diagnostic questions organize the report. First, how much of the observed community population receives a resolved target, and how do excluded groups differ? Second, under the same frozen targets, which classes and conditions explain the proposed model's differences from HGB and matched component controls? The review panel examines whether the supplied membership and interaction evidence supports the structural interpretation of those targets.

## 1. Scope and Evaluation Protocol

This report consolidates the evaluation and diagnostic analyses conducted on the frozen prediction and feature exports.

The predictive evaluation uses the final prediction window only, covering January–September 2018. It contains 1,269 unique community-month samples, 19 model configurations, and three random seeds (42, 43, and 44).

No models were fitted or refitted during these analyses. The exported predictions were validated against the resolved label export and the corresponding feature records. All evaluated predictions matched their expected labels and feature keys.

Predictive metrics use a fixed six-class label set:

- stable
- grow
- shrink
- merge
- split
- dissolve

Macro-F1 is calculated over all six classes with `zero_division=0`. Unresolved labels and terminally censored cases are not converted into event classes and are not included in predictive metrics.

The analyses cover:

- **A1:** Overall and monthly predictive performance.
- **A2:** Performance across community-size and history strata.
- **A3/B:** Label-resolution coverage and resolved/unresolved population diagnostics.
- **Error analysis:** Class-level errors and frequent misclassification pairs.
- **Model comparison:** Matched comparisons between selected model configurations.
- **Paired bootstrap:** Exploratory uncertainty intervals for paired model comparisons.
- **B2 seed agreement:** Prediction consistency across random seeds.

### 1.1. Output Files and Reproducibility

The tables, figures, and validation artifacts for this evaluation are organized under:

- [Midterm 2 output index](tables/midterm2-20261104/README.md)
- [A1 tables](tables/midterm2-20261104/A1/tables/)
- [A2 tables](tables/midterm2-20261104/A2/tables/)
- [A3 tables](tables/midterm2-20261104/A3/tables/)
- [B coverage tables](tables/midterm2-20261104/B/tables/)
- [Error analysis tables](tables/midterm2-20261104/error_analysis/tables/)
- [Matched model comparison](tables/midterm2-20261104/model_comparison/tables/)
- [Paired bootstrap tables](tables/midterm2-20261104/paired_bootstrap/tables/)
- [B2 seed agreement outputs](tables/midterm2-20261104/seed_agreement/)
- [Validation audits](tables/midterm2-20261104/audits/)

Figures are stored separately from the table directories:

- [A1 figures](figures/midterm2-20261104/A1/)
- [A2 figures](figures/midterm2-20261104/A2/)
- [B figures](figures/midterm2-20261104/B/)

The reproducibility scripts are maintained in the repository's `scripts/` directory:

- [run_a1_a2.py](../scripts/run_a1_a2.py)
- [aggregate_a1_a2.py](../scripts/aggregate_a1_a2.py)
- [analyze_seed_agreement.py](../scripts/analyze_seed_agreement.py)

## 2. A1 — Overall and Monthly Performance

### 2.1 Overall performance

The highest overall Macro-F1 among the evaluated configurations was obtained by `hier_lr_dynamic`:

| Metric | Result |
|---|---:|
| Macro-F1 | 0.4117 |
| Accuracy | 0.9046 |
| Unique samples | 1,269 |

Other strong configurations included `A_no_context_drift_matched` (Macro-F1 0.4069), `hier_hgb_dynamic` (0.3880), and `hier_hgb_static` (0.3728).

The validation-selected champion was `hier_hgb_static`, while `hier_lr_dynamic` was the proposed configuration. The final-window result is reported as an evaluation outcome; it does not retrospectively change the validation-based model selection.

Accuracy and Macro-F1 provide different views of performance. The final sample is highly imbalanced: dissolve accounts for 1,167 of 1,269 samples (91.96%). Consequently, accuracy can remain high while performance on less frequent event classes is weak. Macro-F1 gives each of the six classes equal weight, including classes with very small support.

### 2.2 Monthly performance

For `hier_lr_dynamic`, monthly Macro-F1 varied across the final evaluation period:

| Label month | Samples | Macro-F1 |
|---|---:|---:|
| 2018-01 | 144 | 0.3824 |
| 2018-02 | 116 | 0.4349 |
| 2018-03 | 150 | 0.2622 |
| 2018-04 | 147 | 0.2445 |
| 2018-05 | 123 | 0.2881 |
| 2018-06 | 140 | 0.4690 |
| 2018-07 | 146 | 0.3544 |
| 2018-08 | 160 | 0.5496 |
| 2018-09 | 143 | 0.4608 |

The highest monthly Macro-F1 occurred in August, while April had the lowest value. These results indicate variation across the observed months; they should not be interpreted as evidence of a long-term temporal trend.

## 3. A2 — Performance Across Size and History Strata

### 3.1 Community size

The final evaluation sample is concentrated in the smallest size group:

- Size 2: 857 samples.
- Size 3–4: 239 samples.
- Size 5–20: 97 samples.
- Size greater than 20: 76 samples.

For `hier_lr_dynamic`, Macro-F1 by size group was:

| Size group | Macro-F1 |
|---|---:|
| 2 | 0.2078 |
| 3–4 | 0.2380 |
| 5–20 | 0.1658 |
| >20 | 0.3208 |

The results are not monotonic with community size. The group containing 5–20 members consists entirely of dissolve cases in this final sample. Under fixed six-class Macro-F1, absent classes receive zero F1, which lowers the group-level score despite strong performance on dissolve.

Therefore, these results do not support a general claim that larger communities are easier to predict.

### 3.2 Lineage and member-activity history

For `hier_lr_dynamic`:

- Lineage history available: Macro-F1 0.4246 (n=105).
- Lineage history missing: Macro-F1 0.3933 (n=1,164).
- Member-activity history available: Macro-F1 0.4143 (n=730).
- Member-activity history missing or not recorded: Macro-F1 0.2001 (n=539).

These aggregate differences should not be interpreted as causal effects of history availability. The class composition and support differ between groups. In particular, the missing member-activity-history group contains very sparse support for several event classes.

The joint size-by-lineage-history tables provide additional detail, but very small strata require caution. For example, the `5–20 | available` stratum contains only one community-month observation.

## 4. A3/B — Label-Resolution Coverage

### 4.1 Overall coverage

The feature and label-status exports contain 11,745 community-month records:

| Label status | Records |
|---|---:|
| Resolved | 7,490 |
| Unresolved | 4,072 |
| Terminally censored | 183 |
| Total | 11,745 |

Coverage is calculated over resolved and unresolved records, with terminally censored records reported separately:

\[
\text{Coverage} =
\frac{7,490}{7,490+4,072}
= 64.78\%
\]

This is community-month label-resolution coverage. Member-month weighted coverage is calculated separately as 1,417,626 / 1,787,503 = 79.31%. Both measures count repeated observations across months. Terminal censoring is reported separately from observed transitions.

### 4.2 Resolved and unresolved feature distributions

The descriptive comparison found no missing values in the compared feature columns for either the resolved or unresolved groups. This is feature-value completeness, not label-resolution coverage.

Some distributions differ despite identical medians. For example:

- Community size mean: 189.27 for resolved records versus 90.83 for unresolved records.
- Community size median: 2 for both groups.
- Density mean: approximately 0.803 for resolved records versus 0.828 for unresolved records.
- `past_window_fraction` is 1.0 in both groups and therefore does not distinguish the two groups in this export.

The size distributions are highly skewed. Means, standard deviations, quartiles, and within-size-stratum summaries are therefore considered alongside medians.

These comparisons are descriptive. No formal standardized effect sizes or inferential tests, such as SMD, KS tests, or Cramér's V, were produced. The observed differences should not be interpreted as causal explanations for label resolution.

### 4.3 Coverage by history and size

The status tables show that resolved, unresolved, and censored records are distributed across both history and size groups.

The 183 terminally censored records remain a separate status category. They are not treated as unresolved event labels or as dissolve cases.

## 5. Error Analysis

The class-level error analysis uses `hier_lr_dynamic` with seed 42. The three seeds produced identical metrics for this model, so the seed-level results are not treated as independent observations.

| True class | Support | Correct | Recall |
|---|---:|---:|---:|
| dissolve | 1,167 | 1,103 | 0.9452 |
| grow | 19 | 3 | 0.1579 |
| merge | 15 | 3 | 0.2000 |
| shrink | 25 | 12 | 0.4800 |
| split | 39 | 27 | 0.6923 |
| stable | 4 | 0 | 0.0000 |

The model performs strongly on the dominant dissolve class, but recall is substantially lower for grow and merge. Stable has only four observations, so its result is especially uncertain.

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

The dissolve–grow confusion is bidirectional. The model also confuses split with shrink. These errors show why aggregate accuracy alone is insufficient to characterize model behavior.

The hierarchical configuration should not be described as uniformly better across all event classes. Its overall advantage over the matched flat configuration coexists with weaker results on several rare classes.

## 6. Matched Model Comparisons

### 6.1 Proposed and HGB on identical frozen samples

| Model | Final cases per seed | Macro-F1 | Accuracy |
|---|---:|---:|---:|
| Hierarchical LR dynamic, proposed | 1,269 | 0.4117 | 0.9046 |
| Hierarchical HGB dynamic, paired comparator | 1,269 | 0.3880 | 0.9094 |

The paired audit reproduces 29 proposed-only correct and 35 HGB-only correct cases. Both models correctly predict 1,119 cases and both err on 86. A separate table records all 95 prediction disagreements. The complete historical control inventory is retained as supplementary evidence alongside the five reference baselines and the component comparisons.

### 6.2 Matched component contrasts

Three paired contrasts were evaluated:

1. `hier_lr_dynamic` versus `A_no_dynamics_matched`.
2. `hier_lr_dynamic` versus `A_no_context_drift_matched`.
3. `hier_lr_dynamic` versus `A_flat_matched`.

The comparison uses the same final samples and preserves seed pairing.

### 6.3 Paired Macro-F1 intervals

An exploratory paired block bootstrap used 1,000 draws and a block length of two months across nine calendar months.

| Contrast | Macro-F1 difference | 95% interval |
|---|---:|---:|
| Dynamic vs. no dynamics | +0.0474 | [-0.0073, +0.0934] |
| Context-drift configuration vs. no-context-drift | +0.0049 | [-0.0195, +0.0191] |
| Hierarchical vs. flat | +0.0796 | [+0.0292, +0.1321] |

The hierarchical-versus-flat interval is above zero, providing evidence of a positive overall Macro-F1 difference on this final evaluation window.

The intervals for the dynamic-versus-no-dynamics and context-drift contrasts include zero. These comparisons do not establish a clear overall Macro-F1 improvement for those feature changes.

These are exploratory intervals over nine months, not causal estimates or proof of generalization to all resolved records.

### 6.4 Paired correctness outcomes

For the hierarchical-versus-flat comparison:

- Both models correct: 55.40%.
- Proposed model only correct: 35.07%.
- Reference model only correct: 1.34%.
- Both models wrong: 8.20%.

This indicates a substantial paired advantage for the hierarchical configuration in the evaluated sample. However, the class-level analysis shows that the advantage is not uniform: the flat configuration performs better on grow, merge, shrink, and stable in this comparison, while the hierarchical model has a strong advantage on the dominant dissolve class and a benefit on split.

For dynamic versus no dynamics:

- Both models correct: 88.26%.
- Dynamic model only correct: 2.21%.
- No-dynamics model only correct: 3.47%.
- Both models wrong: 6.07%.

The paired correctness rates do not show a broad sample-level advantage for the dynamic configuration. Some rare event classes and larger or history-available strata benefit from the dynamic configuration, while other strata favor the no-dynamics reference.

For the context-drift contrast, the overall paired difference is very small. The result does not provide clear evidence that the context-drift component improves overall performance in this comparison.

Macro-F1 and paired correctness rates weight observations differently. Macro-F1 gives equal weight to classes, whereas paired correctness rates are sample-weighted. Because dissolve dominates the sample, these summaries can lead to different impressions without being contradictory.

### 6.5 Bootstrap limitations

Overall and class-level strata retained at least 984 valid draws. Lineage-history, member-activity-history, and size strata retained all 1,000 draws.

Some draws were dropped for sparse size-history strata, especially `5–20 | available`, which contains one community-month observation. Month-specific confidence intervals were not estimable using the contiguous month-block method because an individual month is not a temporal block sample.

Monthly results are therefore reported descriptively without confidence intervals. Missing intervals are not replaced with zero.

## 7. B2 Random Forest — Seed Agreement

The B2 seed-agreement diagnostic compares predictions from seeds 42, 43, and 44 on the same 1,269 final samples.

| Agreement measure | Result |
|---|---:|
| All three seeds agree | 1,238 (97.56%) |
| At least one seed differs | 31 (2.44%) |
| Seeds 42–43 agree | 98.98% |
| Seeds 42–44 agree | 98.35% |
| Seeds 43–44 agree | 97.79% |

B2 Random Forest predictions are highly consistent across the three tested seeds. Agreement measures prediction stability, not predictive correctness. The three seeds are repeated runs on the same samples and must not be counted as independent observations.

## 8. Limitations

The findings should be interpreted within the following boundaries:

1. **Final-window scope:** A1/A2 predictive metrics use 1,269 unique final samples, not all 7,490 resolved records.
2. **Class imbalance:** Dissolve accounts for 91.96% of the final sample. Rare classes have limited support, particularly stable (n=4).
3. **History-stratum support:** Some subgroup comparisons contain sparse event classes or very small sample sizes.
4. **Descriptive coverage analysis:** A3 compares distributions and status counts but does not include formal effect sizes or inferential tests.
5. **Exploratory bootstrap:** The paired intervals use nine months and a two-month block length. Sparse strata can have dropped draws, and month-specific intervals are not estimable under this method.
6. **No causal interpretation:** Matched comparisons and subgroup differences do not establish that a feature or architecture causes improved performance.
7. **Seed dependence:** Random seeds are repeated runs on the same evaluation samples, not independent test samples.
8. **No full resolved-population prediction export:** The available final predictions do not cover all 7,490 resolved records. Missing predictions are not reconstructed or inferred.

## 9. Label review, adjudication and source-lineage verification

The development panel contains 60 selected cases. Two submitted versions were sealed before comparison. Their pre-discussion agreement was 47/60 (78.33%) and unweighted Cohen kappa was 0.4433. Both reviewers declared AI assistance. The original metadata records the scope of adoption and exposure declarations. These provenance details qualify the evidence when describing label validation.

Phúc and Đăng finalized the 13 disagreements in a separate adjudication record on 6 November. Their decisions were 10 unresolved, two grow and one shrink. Combining those decisions with the 47 initial matches gives the final 60-case panel. The original submissions and pre-discussion agreement remain archived with their SHA-256 hashes.

After the adjudication version was sealed, the coordinator compared its decisions with frozen tracker labels. The final panel agreed with the tracker in 26/60 cases (43.33%). The directions of all 34 discrepancies are retained in the seven-label confusion table.

| Final review decision | Tracker decision | Cases |
|---|---|---:|
| unresolved | dissolve | 24 |
| unresolved | grow | 5 |
| unresolved | merge | 1 |
| grow | unresolved | 2 |
| merge | unresolved | 1 |
| shrink | unresolved | 1 |

The 24 dissolve-to-unresolved discrepancies identify the main interpretation question. A tracker can assign dissolve after its continuity rule rejects successors, while an assessor can retain unresolved when observation or a coherent group continuation remains ambiguous. These cases motivate reporting operational event definitions and observation coverage together. The result alone establishes neither a corpus collection defect nor disappearance of a social group. The panel was stratified for diagnosis, so its matching rate applies to these 60 cases.

The source-month lineage check found 52 focal communities with no accepted predecessor, five with an ambiguous lineage reset, and three with unique continuation. Reconstructed predecessor counts, stored age and missing-history flags matched the frozen feature values. Forty-three cases lacked accepted lineage while member-activity history was available. Source age checks reused the prior audited age and the frozen inclusion-pair table. This verifies saved semantics within that scope. The anonymous graph audit separately checked all 13 disputed cases for membership, overlap, edges and observation consistency.

### Supplementary six-case assessment

A separate six-case development sample was prepared with seed 20261109. One community was selected within each size stratum 2–4, 5–20 and above 20 in each of April and May 2017. The earlier 66 pilot/main case keys were excluded. Target labels and model predictions were withheld during selection and assessment. Complete anonymous memberships, incident edges, successor/predecessor overlap and per-member observation flags were available.

At the user's request, the assistant assessed all six cases and recorded the evidence, confidence and rationale. The supplementary decisions were three unresolved, one grow, one shrink and one observed-network dissolve, all with medium confidence. The grow/shrink interpretations rely on a dominant surviving interaction core despite partial source retention. The dissolve interpretation concerns absence in the next-month reply and authored-record channels within the declared observation scope.

This adds six automated case interpretations to the technical diagnostic record. Actual human decisions on these six cases remain unrecorded. The original blank human worksheet is retained separately. The adjacent monthly transitions can reuse underlying memberships, which limits independence among cases. These supplementary decisions enter neither the original 60-case agreement nor its 26/60 tracker comparison. The assessment remains a separately identified exploratory supplement.

The aggregate counts and sampling/provenance scope are retained in [the supplementary assessment summary](tables/week3-review-20261109/supplementary-assessment-summary.json).

Aggregate review results and source hashes are available in [the review tables](tables/week3-review-20261109/review-summary.json), [the tracker confusion table](tables/week3-review-20261109/review-tracker-confusion.csv), [the lineage table](tables/week3-review-20261109/source-lineage-summary.csv) and [provenance](tables/week3-review-20261109/provenance.json).

## 10. Week 3 evidence ledger

| Lecturer feedback or planned output | Evidence available | Acceptance and remaining work |
|---|---|---|
| Explain how graph and labels are constructed | Frozen source manifests, declared reply projection, detector/tracker rules and lineage examples | Technical preparation complete. Operational label interpretation remains explicit. |
| Check ambiguous dissolve and unresolved cases | 60-case sealed submissions, 13-case adjudication and post-lock tracker comparison | Processing complete for the declared AI-assisted submissions. A six-case automated supplement is documented separately. Independent human validation remains open. |
| Explain unresolved exclusions and applicability | Full-study community-month coverage 64.78%, member-month coverage 79.31%, 4,072 unresolved and 183 terminal censored | Aggregate and month/size/history coverage are available. Recipient-side graph audit evidence must retain the run manifest. |
| Explain grow/merge errors and HGB comparison | 1,269 final keys per seed, four correctness groups, 64 correctness contrasts and 95 prediction disagreements | Frozen-data replay reproduced the counts. Interpret 16 selected illustrations within their documented sampling skew. |
| Explain performance by class, month and history | A1/A2 tables, six-class metrics, per-class support and exploratory paired intervals | Complete for the final prediction window. Final-window metrics cover 1,269 resolved cases. |
| Deliver a coherent diagnosis | Coverage correction, this review section, existing mechanism analysis and aggregate inventories | Integrated in this report with matched tables, source hashes and diagnostic findings. |

## 11. Integrated diagnostic conclusions

### Label applicability and observation

The study assigns resolved labels to 7,490 of 11,562 observed transitions, giving community-month coverage of 64.78%. Weighting by community size gives member-month coverage of 79.31%. The 183 terminal communities remain censored. Together these measures define the population to which forecasting metrics apply and the observation mass excluded by unresolved labels.

The review panel raises an additional interpretation issue. Its final 60-case decisions contain 50 unresolved, six merge, three grow and one shrink. Twenty-six decisions agree with the tracker. Of the 34 differences, 24 are tracker-dissolve cases retained as unresolved by the review process. The panel was selected within machine-event strata, so these counts characterize the inspected cases. They identify ambiguity between a rule-defined lack of continuity and confidence in an observed structural event. The underlying graph audit detected no inconsistency in the supplied memberships, overlaps, edges or observation flags for the 13 disputed cases.

### Forecast errors and the HGB comparison

On 1,269 final samples per seed, the proposed hierarchical LR dynamic model has Macro-F1 0.4117, compared with 0.3880 for hierarchical HGB dynamic. The paired outcomes are 1,119 both correct, 29 proposed-only correct, 35 HGB-only correct and 86 both wrong. These counts repeat identically across seeds. Among all different predicted labels, 95 cases differ, including 31 cases where both predictions are wrong. Macro-F1 and the number of correct predictions emphasize different aspects of this imbalanced six-event task.

Grow and merge remain the clearest error groups. Proposed predicts dissolve for 14/19 grow cases and 8/15 merge cases. The HGB comparator does so for 12/19 and 9/15 respectively. This locates the error concentration in the dissolve-versus-event decision and in the available community history. It also shows that the two models exchange errors within the same rare classes.

### History and component evidence

Source-month lineage matches the saved predecessor and age semantics across the 60 audited focal communities. Fifty-two lack an accepted predecessor, while five reset age under ambiguous lineage and three have unique continuation. Forty-three cases have no accepted lineage but retain member-activity history. These channels require separate interpretation when analyzing performance strata.

The exploratory full-study component contrasts give a dynamic-versus-no-dynamics Macro-F1 difference of +0.0474 with interval [-0.0073, +0.0934]. The context-drift difference is +0.0049 with interval [-0.0195, +0.0191]. The matched hierarchical-versus-flat difference is +0.0796 with interval [+0.0292, +0.1321]. The clearest positive component evidence in this final window concerns the hierarchical decision architecture. The feature-group contributions have wider uncertainty and heterogeneous subgroup behavior.

### Completed diagnostic record

Week 3 has produced frozen input contracts, review submission receipts and checksums, pre-discussion agreement, a separate adjudication, source-lineage checks, full-population coverage, a paired error analysis on the final window and a separately documented six-case automated supplement. Repeated seeds refer to the same communities. The 16 selected error illustrations emphasize early months and larger groups, which is documented alongside their selection procedure. Review provenance, class support, unresolved eligibility and diagnostic sampling delimit the conclusions throughout the report.

The subsequent experimental stage can use this record to justify a bounded change and its matched evaluation. Model changes, fitting and subsequent-stage ablation results are outside the results consolidated here.
