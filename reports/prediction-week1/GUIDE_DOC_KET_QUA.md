# Guide to Evaluation Results



## 1. Purpose



This guide explains how to run the prediction pipeline and interpret its evaluation outputs. The current experiment uses synthetic data to validate the evaluation workflow, not to demonstrate performance on real Reddit communities.



## 2. Run the pipeline



From the repository root, run:



```powershell

& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config .\configs\prediction.toml --run-id lan-eval-guide-20261018

```



Use a unique run ID for each new experiment.



## 3. Output files



| File | Description |

|---|---|

| `samples.csv` | Generated sample table |

| `split.csv` | Temporal split assignments |

| `split_summary.csv` | Sample counts by split |

| `metrics.csv` | Metrics by model and split |

| `per_class.csv` | Per-class precision, recall, F1 and support |

| `confusion_<model>_<split>.csv` | Six-class confusion matrix |

| `evaluation_notes.md` | Metric definitions and evaluation notes |



## 4. Metrics



- `macro_f1`: mean F1 over classes present in the true labels.

- `macro_f1_six`: mean F1 over all six event classes.

- `balanced_accuracy`: mean recall over classes present in the true labels.

- `n`: number of evaluated predictions.

- `n_classes_present`: number of classes present in the true labels.



Compare models on the same split and consider the class distribution when interpreting results.



## 5. Per-class metrics and confusion matrices



`per_class.csv` reports precision, recall, F1 and support for each model, split and event label.



In confusion matrices, rows represent true labels and columns represent predicted labels. Diagonal values are correct predictions; off-diagonal values are misclassifications.



A class with zero true support requires careful interpretation. Its class-level metrics do not establish successful detection.



## 6. Verified development run



Run ID: `lan-eval-guide-20261018`



The run completed the table, split, baseline and evaluation stages. It processed 4,572 prediction rows and generated 9 model/split metric rows.



## 7. Limitation



The current data is synthetic. These outputs validate the evaluation workflow and must not be reported as measured predictive performance on real Reddit communities. Additional models and real Reddit features remain unfinished.
