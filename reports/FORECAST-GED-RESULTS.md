# GED adaptation and history-feature results

Executed 2026-10-16. Canonical local delivery: `artifacts/core/forecast-ged-history-v3`.
The schema and consumption instructions are in [the handoff contract](FORECAST-HANDOFF.md).

## Data and eligibility

- 2,320 community-month feature rows, including the unlabeled final month.
- 2,065 source-community transition rows, all retained in labels.csv.
- 1,333 eligible samples; 732 weak-overlap cases explicitly excluded, with reasons.
- Training: 762 samples, label months February-September 2015.
- Held out: 571 samples, label months October-December 2015.
- Twelve input snapshots retain the previously reproduced upstream graph reference.

## Scores

| Model | Six-class macro-F1 | Balanced accuracy on present test classes |
|---|---:|---:|
| majority | 0.159672 | 0.200000 |
| logistic_regression | 0.360540 | 0.482190 |

| Event | Train | Test |
|---|---:|---:|
| stable | 1 | 0 |
| grow | 10 | 8 |
| shrink | 20 | 12 |
| merge | 38 | 20 |
| split | 22 | 6 |
| dissolve | 671 | 525 |

## Interpretation

These are descriptive results of the GED-strength topology adaptation and seven past-only history features, not a verbatim GED reproduction or HeTCo result. The test set has no stable samples, and 525/571 held-out labels are dissolve. Logistic Regression correctly classifies 5/12 shrink and 6/6 split samples, but 0/8 grow and 0/20 merge samples. Reporting only aggregate accuracy would conceal those failures.

The 732 excluded cases represent 35.45% of all source transitions. Report this coverage loss with any score. The model is not evaluated on those unresolved cases. Original Jaccard results use a different label reference and population, so the new score cannot be interpreted as a controlled improvement over the old 0.309.

Parameters were fixed at alpha=beta=0.5, dissolve=0.1, numeric tolerance 1e-12. No parameter search used held-out scores. Six expanding-window development folds are restricted to training label months. Since the period was already inspected during fallback development, the held-out scores are descriptive, not a fresh confirmatory result.

The delivery includes per-class precision/recall/F1/support, full confusion matrices, individual errors, explicit split assignments and monthly support. Independent consumer checks recompute confusion matrices and macro-F1 from saved predictions. HeTCo, original GED social-position iteration and original pair-event classification remain unimplemented.

## Software verification

Full repository suite: 148 discovered; 146 passed; two upstream notebook-plot tests skipped because optional notebook dependencies are absent. Forecast/tracking/history coverage includes 38 tests with no skips. Local log: `artifacts/forecast-delivery-suite.log`. Prior fallback runs and reports remain historical evidence rather than being overwritten.
