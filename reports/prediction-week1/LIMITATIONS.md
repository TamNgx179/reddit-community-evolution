# Limitations and Remaining Work

## 1. Synthetic data

The current pipeline uses synthetic data. The results validate the evaluation workflow and software integration only. They must not be presented as evidence of predictive performance on real Reddit communities.

## 2. Model coverage

The current pipeline includes the available baseline models. The following planned components remain unfinished:

- B2 Random Forest (Phuc).
- B5 Gradient Boosting (Phuc).
- HeTCo (Thanh).
- Real Reddit features (Thanh).

Metrics from the current run therefore do not represent a comparison of all planned models.

## 3. Temporal split and leakage

Samples are assigned to temporal splits using `label_month`. Sample validation checks data consistency and potential feature leakage. These checks reduce known risks but do not prove that every possible source of leakage has been eliminated.

The fixture `tests/fixtures/prediction/samples_leaky.csv` is an intentionally leaky negative-control fixture. It must not be used as valid training or evaluation data.

## 4. Metric interpretation

- `macro_f1` averages F1 over classes present in the true labels.
- `macro_f1_six` averages F1 over all six event classes.
- `balanced_accuracy` averages recall over classes present in the true labels.
- Per-class metrics for a class with zero true support require caution and do not demonstrate successful detection of that class.

Metrics should be compared on the same split and interpreted alongside class support and confusion matrices.

## 5. Pipeline completion status

The run status `complete_through_baselines` means the available table, split, baseline and evaluation stages completed. It does not mean that every planned model or the real-data workflow is complete.

## 6. Remaining work

- Implement and integrate the remaining planned models and real Reddit features.
- Perform cross-review of the evaluation implementation and outputs.
- Complete the demo and presentation before the project code freeze.
- Re-evaluate the workflow with appropriate real Reddit data when available.
