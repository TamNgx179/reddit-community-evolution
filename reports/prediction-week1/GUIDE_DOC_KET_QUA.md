# Guide to Evaluation Results

## 1. Purpose

This guide explains how to run the prediction pipeline and interpret its evaluation outputs.

The current week-one workflow uses synthetic data to validate the prediction and evaluation pipeline. It does not establish predictive effectiveness on real Reddit communities.

## 2. Run the pipeline

From the repository root, run:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config .\configs\prediction.toml --run-id lan-week1-final-20261019
```

Use a unique run ID for each new run. The run ID identifies the generated artifacts under `artifacts/prediction/`.

## 3. Output files

| File | Description |
|---|---|
| `samples.csv` | Generated sample table |
| `predictions.csv` | Baseline predictions |
| `split.csv` | Temporal split assignments |
| `split_summary.csv` | Sample counts by split |
| `metrics.csv` | Metrics by model and split |
| `per_class.csv` | Per-class precision, recall, F1 and support |
| `confusion_<model>_<split>.csv` | Confusion matrix for a model and split |
| `feature_catalog.csv` | Feature metadata used by the pipeline |
| `manifest.json` | Run metadata |
| `evaluation_notes.md` | Metric definitions and evaluation notes |

The exact output files may depend on the pipeline configuration and implemented models.

## 4. Metrics

- `macro_f1`: Mean F1 over classes present in the true labels.
- `macro_f1_six`: Mean F1 over all six event classes, according to the implemented metric policy.
- `balanced_accuracy`: Mean recall over classes present in the true labels.
- `n`: Number of evaluated predictions.
- `n_classes_present`: Number of classes present in the true labels.

Compare models using the same split and identical sample keys. Consider class distribution and the treatment of classes absent from the true labels when interpreting results.

## 5. Per-class metrics and confusion matrices

`per_class.csv` reports precision, recall, F1 and support for each model, split and event label.

In confusion matrices, rows represent true labels and columns represent predicted labels. Diagonal values represent correct predictions; off-diagonal values represent misclassifications.

A class with zero true support requires careful interpretation. Its class-level metrics alone do not establish successful detection.

## 6. Latest verified development run

Run ID: `lan-week1-final-20261019`

The pipeline output reported:

- 4,572 prediction rows.
- 9 model/split metric rows.
- Evaluation stage completed.
- Generated evaluation outputs include `metrics.csv`, `per_class.csv`, `split_summary.csv`, confusion matrices and `evaluation_notes.md`.

The complete unit test suite was also run:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: 253 tests run, `OK`, with no test failures or errors.

Sample validation tests were run separately:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.unit.test_sample_checks -v
```

Result: 14 tests passed.

These results provide evidence for implementation and pipeline validation. They should not be interpreted as proof of predictive performance on real Reddit data.

## 7. Research notebook status

`notebooks/prediction/00_research_plan.ipynb` remains a research template with status `template_not_executed`.

It defines the research question, temporal split and leakage principles, baseline fairness requirements, and evidence needed for future experiments. Its deliberate `NotImplementedError` cell means it is not currently an executable experiment.

Do not report this notebook as a completed experiment. A future experiment should record its configuration, seed, source revision, environment, manifest and actual results.

## 8. Limitations and next steps

- Current development data is synthetic.
- The current results validate pipeline behavior, not real-world Reddit predictive effectiveness or H3.
- B2 Random Forest, B5 Gradient Boosting, HeTCo and real Reddit features remain unfinished in the current pipeline.
- Further research should use appropriate real data, preserve temporal causality, compare identical sample keys and report negative results as well as positive ones.
- Cross-review and final demo/slide preparation remain outstanding.
