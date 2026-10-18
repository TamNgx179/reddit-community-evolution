# Prediction Evaluation — Demo Guide



## 1. Overview



This demo shows the temporal split, sample validation, baseline prediction and evaluation workflow for the Reddit community evolution project.



**Important:** The current pipeline uses synthetic data. This demo validates the workflow, not predictive performance on real Reddit communities.



## 2. Requirements



- Windows with PowerShell.

- Python environment available at `.venv`.

- Project dependencies installed.

- Run commands from the repository root.



## 3. Run the demo



Execute:



```powershell

& .\.venv\Scripts\python.exe -m reddit_sna.pipelines.prediction --config .\configs\prediction.toml --run-id lan-eval-final-20261018

```



This run ID refers to the existing evaluation run. To generate a fresh run, choose a new ID instead of reusing it.



## 4. Expected workflow



1. Generate the sample table.

2. Validate samples and assign temporal splits.

3. Generate predictions from available baseline models.

4. Validate predictions against the split.

5. Calculate aggregate and per-class metrics.

6. Export confusion matrices and evaluation notes.



The current pipeline should report that it completed through the available baselines.



## 5. Check the output



The existing successful run is located at:



```text

artifacts/prediction/lan-eval-final-20261018/

```



Check these files:



- `samples.csv`

- `split.csv`

- `split_summary.csv`

- `metrics.csv`

- `per_class.csv`

- `evaluation_notes.md`

- `confusion_<model>_<split>.csv`



The exact set of confusion matrix files depends on the model/split combinations produced by the run.



## 6. Run the relevant unit tests



Run the sample validation tests:



```powershell

& .\.venv\Scripts\python.exe -m pytest .\tests\unit\test_sample_checks.py -v

```



Run the metrics tests:



```powershell

& .\.venv\Scripts\python.exe -m pytest .\tests\unit\test_metrics.py -v

```



Run the temporal split tests:



```powershell

& .\.venv\Scripts\python.exe -m pytest .\tests\unit\test_splits.py -v

```



Run all unit tests:



```powershell

& .\.venv\Scripts\python.exe -m pytest .\tests\unit -v

```



## 7. Negative-control test



The fixture `tests/fixtures/prediction/samples_leaky.csv` intentionally includes a `future_feature` feature with `t+1` availability.



The test `test_leaky_fixture_is_detected` verifies that the sample validation logic detects this leakage. The fixture is a test artifact, not a valid dataset for model training.



## 8. Current status



The run `lan-eval-final-20261018` successfully processed 4,572 prediction rows and generated 9 model/split metric rows. The table, split, baseline and evaluation stages completed.



Remaining work includes the planned Random Forest and Gradient Boosting baselines, HeTCo, and real Reddit features.
