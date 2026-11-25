# Anh — Locked Evaluation Protocol

## 1. Purpose and Scope

This evaluation script is designed to assess model predictions for the Trâm–Anh evaluation task.

The script evaluates frozen prediction outputs only. It does not train models, modify model parameters, select models, tune hyperparameters, or alter predictions.

The purpose is to provide a consistent evaluation protocol across models, seeds, months, and cohorts, while ensuring that model comparisons are performed on aligned samples.

The evaluation is prediction-blind during implementation and testing. All unit tests use synthetic data and do not load or inspect predictions from Trâm.

---

## 2. Evaluation Metrics

### 2.1 Fixed six-class label set

The evaluation uses the following fixed class order:

1. stable
2. grow
3. shrink
4. merge
5. split
6. dissolve

All metrics and confusion matrices use this class order, regardless of which classes are present in the evaluated data.

### 2.2 Macro-F1

Macro-F1 is calculated across all six classes by taking the arithmetic mean of the class-level F1 scores.

Classes absent from the ground truth are retained in the calculation and assigned an F1 score of zero. This prevents the evaluation from artificially improving when a class is absent from a particular month or cohort.

Macro-F1 gives equal weight to all six classes rather than allowing classes with larger support to dominate the overall score.

### 2.3 Per-class metrics

The evaluation reports the following metrics for each class and month:

- **Precision:** proportion of predictions for a class that are correct.
- **Recall:** proportion of ground-truth instances of a class that are correctly predicted.
- **F1:** harmonic mean of precision and recall.
- **Support:** number of ground-truth instances belonging to the class.

All six classes are included in the per-class outputs, even when a class has zero support in a given month.

---

## 3. Input Data Contract

The evaluator accepts one UTF-8 CSV file containing frozen predictions.

Required columns:

`reference_id, feature_month, community_id, label_month, label_reference_id, cohort, model, seed, y_true, y_pred`

### Field descriptions

- `reference_id`: identifier for the feature or observation reference.
- `feature_month`: month associated with the input features.
- `community_id`: community identifier.
- `label_month`: target month being evaluated.
- `label_reference_id`: identifier of the tracker-label reference used for the ground truth.
- `cohort`: explicit study or cohort identifier.
- `model`: model identifier.
- `seed`: integer seed associated with the prediction run.
- `y_true`: ground-truth evolution label.
- `y_pred`: predicted evolution label.

### Alignment requirements

All models compared within a cohort must have:

- The same seed set.
- The same evaluation sample keys.
- The same ground-truth labels for corresponding samples.

The label reference is retained in the sample key to prevent samples from different tracker-label references from being accidentally mixed.

### Validation and failure conditions

The evaluator performs strict validation before producing results.

Invalid input includes:

- Missing required columns.
- Blank required values.
- Invalid class labels.
- Invalid month formats.
- A target month that does not immediately follow its feature month.
- Duplicate prediction rows.
- Missing samples for a model.
- Misaligned sample keys between models.
- Inconsistent ground-truth values across corresponding samples.
- Inconsistent seed sets within a cohort.

The script fails explicitly when these conditions are detected. It does not silently intersect model datasets to make an invalid comparison appear valid.

---

## 4. Evaluation Outputs

The evaluation writes its outputs into a new directory. The output directory must not already exist.

### 4.1 `overall.csv`

Reports six-class Macro-F1 for each cohort, model, and seed across the evaluated period.

This output provides an overall performance summary while retaining the seed-level results.

### 4.2 `monthly.csv`

Reports six-class Macro-F1 by month, cohort, model, and seed.

This allows model performance to be inspected over time rather than relying exclusively on an aggregate score.

### 4.3 `per_class_month.csv`

Reports class-level precision, recall, F1, and support for all six classes by month.

This output is used to identify classes that are difficult to predict, classes with low support, and months where particular classes are absent.

### 4.4 `confusion_month.csv`

Contains monthly six-class confusion counts.

The confusion matrix preserves the fixed label order and makes it possible to examine which evolution classes are confused with one another.

### 4.5 `confusion_overall.csv`

Contains the six-class confusion counts aggregated over the evaluation period.

This provides an overall view of prediction errors across the six evolution classes.

### 4.6 `paired_bootstrap.csv`

Reports paired comparisons between every unordered model pair present within each cohort.

For each pair, the output includes:

- Cohort identifier.
- Model A.
- Model B.
- Observed Macro-F1 difference (Model A minus Model B).
- Lower bound of the 95% confidence interval.
- Upper bound of the 95% confidence interval.
- Bootstrap configuration and availability status.

Pairwise comparisons are calculated separately for each cohort. Models from different cohorts are never compared against one another.

---

## 5. Paired Block Bootstrap Protocol

### 5.1 Configuration

The bootstrap uses the following frozen configuration:

- Number of bootstrap draws: 2,000.
- Calendar block length: 3 consecutive months.
- Confidence level: 95%.
- Confidence interval method: percentile.
- Lower percentile: 2.5%.
- Upper percentile: 97.5%.
- RNG seed: 2026.

### 5.2 Calendar-month blocks

Each bootstrap replicate resamples contiguous blocks of three calendar months with replacement.

Month blocks preserve local temporal continuity better than independently resampling individual months.

Calendar gaps are represented as zero-count months on the calendar axis, so block sampling follows calendar continuity rather than treating non-consecutive observed months as adjacent.

### 5.3 Paired sampling across models

Within a cohort, the same sampled month-block sequence is applied to every model and seed in a bootstrap replicate.

This shared sampling preserves the paired nature of the comparison: models are evaluated using the same resampled temporal observations rather than independently sampled months.

### 5.4 Cohort isolation

Each cohort is evaluated independently.

Model names and seed sets are resolved within their respective cohorts. Cohorts may therefore contain different model names and different seed IDs without affecting the bootstrap evaluation of another cohort.

No samples, predictions, model lists, or seed lists are pooled across cohorts.

Each cohort uses a reproducible random-number generator initialized with the configured seed.

### 5.5 Bootstrap score calculation

For each bootstrap replicate:

1. Sample contiguous calendar month blocks with replacement.
2. Apply the same month draw to every model and seed within the cohort.
3. Aggregate the six-class confusion matrices for the sampled months.
4. Calculate the six-class Macro-F1 for each seed.
5. Average seed-specific scores to obtain the bootstrap model score.
6. Calculate the difference between the two model scores for each model pair.

The paired bootstrap distribution is constructed from the resulting model-score differences.

### 5.6 Confidence intervals

For each model pair and cohort, the evaluator calculates a separate percentile confidence interval from the 2,000 paired bootstrap differences.

The 95% confidence interval is defined by the 2.5th and 97.5th percentiles of the bootstrap distribution.

The observed difference is calculated as:

**Model A Macro-F1 − Model B Macro-F1**

A positive difference favors Model A; a negative difference favors Model B.

If a cohort has fewer than three calendar months, its bootstrap confidence interval is reported as unavailable rather than producing an invalid or fabricated interval.

---

## 6. Interpretation and Limitations

The bootstrap confidence intervals describe variation across the observed temporal evaluation series under the specified resampling protocol.

They should not be interpreted as proof of:

- Independent observations.
- Generalization to unseen communities or unseen cohorts.
- Causal superiority of one model.
- Statistical independence between adjacent months.
- Performance outside the evaluated period.

Because months may be temporally dependent, the block-bootstrap design retains short temporal sequences rather than assuming that every month is an independent observation.

Model comparisons should be interpreted together with the overall metrics, monthly metrics, class-level support, and confusion matrices.

---

## 7. Synthetic Test Protocol

All unit tests use synthetic data.

Tests cover:

- Missing classes in ground truth.
- Six-class Macro-F1 with absent classes assigned zero F1.
- Classwise zero support.
- Per-class metric completeness.
- Strict sample-key and ground-truth alignment.
- Rejection of missing model samples.
- Rejection of duplicate rows.
- Bootstrap repeatability under a fixed RNG seed.
- Paired month-block bootstrap behavior.
- Bootstrap configuration of 2,000 draws and 3-month blocks.
- Insufficient-month handling.
- Cohort isolation when different cohorts contain different model names and seed IDs.

The synthetic tests do not load or inspect any predictions from Trâm.

---

## 8. Frozen Evaluation Configuration

The following configuration is fixed for this candidate version:

| Parameter | Value |
|---|---|
| Number of classes | 6 |
| Class order | stable, grow, shrink, merge, split, dissolve |
| Macro-F1 | Fixed six-class average |
| Absent class F1 | 0 |
| Bootstrap type | Paired contiguous calendar block |
| Block length | 3 months |
| Bootstrap draws | 2,000 |
| Confidence interval | 95% percentile |
| CI percentiles | 2.5%, 97.5% |
| RNG seed | 2026 |
| Model comparison | All unordered model pairs within each cohort |
| Cohort handling | Separate evaluation; no pooling |
| Training or model selection | Not performed |

---

## 9. SHA-256 Fingerprints

The fingerprints identify the code and test files used for this candidate evaluation version. They are used to verify file integrity and detect accidental changes.

```text
4cb9172da68a21fc09272321ecffe59259edc4e087ca5099c6e7d57d48af39d3  src/reddit_sna/evaluation/locked_metrics.py
99567b005fcfb7da799acf28efa70fc36268d360ba973f9e7dfdf521c78b606b  scripts/run_locked_evaluation.py
2f90a6cf27a15c08c1fbc037594ef0f1de3ca96038a43b9129b98212c05225f8  tests/unit/test_locked_evaluation.py
```

Any modification to these files invalidates the corresponding fingerprint and requires integrity verification again.

---

## 10. Freeze Status

This candidate version has been tested using synthetic data.

All five unit tests pass, including the additional test for cohort-specific models and seed sets.

All three SHA-256 fingerprints have been verified on the local project files.

No predictions from Trâm have been evaluated using this candidate version.

This version is intended to serve as the fixed evaluation protocol for the Trâm–Anh prediction comparison. Any subsequent code or test change must be treated as a new evaluation version, with new tests and fingerprints, before predictions are examined.