# Limitations and Remaining Work

## 1. Synthetic data

The current pipeline uses synthetic data. The results validate the evaluation workflow and software integration only. They must not be presented as evidence of predictive performance on real Reddit communities.

## 2. Model coverage

The current pipeline includes the available baseline models:

B1 Majority.

B1 Persistence.

B4 Logistic Regression.

The following planned components remain unfinished:

- B2 Random Forest (Phuc).
- B5 Gradient Boosting (Phuc).
- HeTCo (Thanh).
- Real Reddit features (Thanh).

Metrics from the current run therefore do not represent a comparison of all planned models.

## 3. Temporal split and leakage

Samples are assigned to temporal splits using `label_month`. The current run contains 1,000 training samples across 23 labeled months, 263 validation samples across 6 labeled months, and 261 test samples across 6 labeled months. Another 46 unlabeled samples are excluded from evaluation.

Sample validation checks data consistency and potential feature leakage. These checks reduce known risks but do not prove that every possible source of leakage has been eliminated. The exact temporal boundaries and feature availability should be reviewed before final acceptance.

The fixture `tests/fixtures/prediction/samples_leaky.csv` is an intentionally leaky negative-control fixture. It must not be used as valid training or evaluation data.

## 4. Metric interpretation

- `macro_f1` averages F1 over classes present in the true labels.
- `macro_f1_six` averages F1 over all six event classes.
- `balanced_accuracy` averages recall over classes present in the true labels.
- Per-class metrics should be interpreted alongside the true class support and confusion matrices. A class receiving no positive predictions has zero precision and recall under the current evaluation results and is not being successfully detected.

All six classes are present in each evaluated split in the current run. Therefore, macro_f1 and macro_f1_six have the same reported values for this run. This equality should not be assumed for every future run.

On the current test split, B1 Persistence has macro-F1 of approximately 0.2557, B4 Logistic Regression approximately 0.2160, and B1 Majority approximately 0.1125. B1 Persistence does not predict split or dissolve on the test split, while B4 Logistic Regression does not correctly detect merge or dissolve in the reported test confusion matrix. These results illustrate why aggregate metrics alone are insufficient.

Metrics should be compared on the same split and interpreted alongside class support and confusion matrices. Since the dataset is synthetic, these comparisons are not evidence of real-world Reddit forecasting performance.

## 5. Pipeline completion status

The run status `complete_through_baselines` means the available table, split, baseline and evaluation stages completed. It does not mean that every planned model or the real-data workflow is complete.

The run manifest records Git revision 007696493ee1d05921dc8c0d80320ce6dd6d8185, whereas the currently reported repository HEAD is ac081e6. The current run should therefore be regenerated with a new run ID on the intended final code revision before its outputs are treated as final verification evidence.

## 6. Remaining work

- Implement and integrate the remaining planned models and real Reddit features.
- Perform cross-review of the evaluation implementation and outputs.
- Verify temporal boundaries, feature-time constraints, and leakage checks.
- Re-run the demo from the intended final code revision and retain its manifest and artifacts.
- Complete the shared research notebook and presentation before the project code freeze.
- Re-evaluate the workflow with appropriate real Reddit data when available.
