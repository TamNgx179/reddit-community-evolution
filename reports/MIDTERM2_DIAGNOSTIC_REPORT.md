# Midterm 2 — Evaluation and Diagnostic Analysis Report

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

This is member-month weighted coverage. A member or community may contribute records in multiple months; the percentage should not be interpreted as the proportion of unique members that were resolved.

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

Three paired contrasts were evaluated:

1. `hier_lr_dynamic` versus `A_no_dynamics_matched`.
2. `hier_lr_dynamic` versus `A_no_context_drift_matched`.
3. `hier_lr_dynamic` versus `A_flat_matched`.

The comparison uses the same final samples and preserves seed pairing.

### 6.1 Paired Macro-F1 intervals

An exploratory paired block bootstrap used 1,000 draws and a block length of two months across nine calendar months.

| Contrast | Macro-F1 difference | 95% interval |
|---|---:|---:|
| Dynamic vs. no dynamics | +0.0474 | [-0.0073, +0.0934] |
| Context-drift configuration vs. no-context-drift | +0.0049 | [-0.0195, +0.0191] |
| Hierarchical vs. flat | +0.0796 | [+0.0292, +0.1321] |

The hierarchical-versus-flat interval is above zero, providing evidence of a positive overall Macro-F1 difference on this final evaluation window.

The intervals for the dynamic-versus-no-dynamics and context-drift contrasts include zero. These comparisons do not establish a clear overall Macro-F1 improvement for those feature changes.

These are exploratory intervals over nine months, not causal estimates or proof of generalization to all resolved records.

### 6.2 Paired correctness outcomes

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

### 6.3 Bootstrap limitations

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

## 9. Overall Conclusions

The final-window evaluation shows that `hier_lr_dynamic` achieves the highest observed overall Macro-F1 among the evaluated configurations, while the hierarchical-versus-flat paired comparison has a positive exploratory 95% interval.

However, model performance is strongly affected by class imbalance. The dominant dissolve class is predicted substantially better than rare event classes, and the hierarchical advantage is not uniform across all classes.

The tested dynamic-feature contrast does not establish a clear overall Macro-F1 improvement, and the context-drift contrast shows only a negligible difference. Subgroup results suggest heterogeneous behavior across event classes, size groups, and history availability.

The coverage analysis also shows that only 64.78% of eligible community-month records have resolved labels. Resolved and unresolved records differ descriptively in several feature distributions, but the current analysis does not establish why those differences occur.

Overall, these results support a careful interpretation of predictive performance, class-specific errors, subgroup support, and label-resolution coverage. They should be treated as evidence about the frozen final evaluation window rather than as estimates that automatically generalize to the entire resolved population.