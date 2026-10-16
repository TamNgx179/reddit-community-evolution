# Tracking and forecasting

The current delivery is documented in [schema-2 handoff](FORECAST-HANDOFF.md),
including the GED adaptation, history features and verified consumer. HeTCo remains
unimplemented. The section below describes the original Jaccard fallback, which
consumes verified graph/detection runs without rerunning detection. This fallback
uses Jaccard >= 0.25 (fixed before evaluation). All qualifying links are kept.
For each source community: no successor -> dissolve; multiple successors ->
split; one successor with multiple predecessors -> merge; otherwise exact
member counts determine grow/shrink/stable. Split takes precedence in many-to-many
cases. Births are not source-community forecasting samples. Disappearance from
the observed reply graph is not proof of social dissolution.

Community IDs are local to each month. Joins use the verified canonical reference
and pseudonymous users inside a single cohort. Never join quarter and annual IDs.
Inputs must cover consecutive months. Empty snapshots are retained, not skipped.

Features use only the current month's memberships and undirected R graph:
size, internal edge count, internal weight, boundary weight and internal density.
Each row labels the source community's transition to the next month. No final-month
label is invented. Features do not use target size, overlap or future labels.

The split uses **label month**: train < `--test-start`, test >= it. Scaling and
Logistic Regression fit only on train. Majority is also reported, with a Majority
fallback for single-class training. Seeds default to 42. There is no hyperparameter
search. Macro-F1 and confusion matrices always use the six declared event classes;
absent classes receive zero F1. Per-class support is included. Labels are
tracker-derived pseudo-labels, so these metrics evaluate prediction of this rule,
not tracking accuracy against independently annotated truth.

## Run with Tam's local artifacts

Install Python 3.11+ and `python -m pip install -e ".[forecast]"`.
To obtain all 15 declared source archives from the official Cornell index, run
`python scripts/download_reddit.py --download`. Without `--download`, the script
only lists resolved URLs and sizes. Downloads stay under `data/raw`, with a local
SHA-256/CRC manifest. Existing completed archives are checked rather than replaced.
Install `.[graph,forecast]` to rebuild detection as well as forecasting.
From the repository root, run (one line):

```powershell
python -m reddit_sna forecast --graph-run artifacts/core/reddit-2015-ordered-graphs-v1 --detection-run artifacts/core/reddit-2015-ordered-detection-v1 --output artifacts/core/forecast-001 --test-start 2015-10
```

The October boundary is an initial chronological holdout, not a tuned optimum.
Inspect class support before making any forecasting claim. If no train/test rows
exist the command fails rather than fabricating scores. Existing output directories
cannot be overwritten. Raw Reddit data and generated artifacts are not committed.

Outputs: `tracking.csv`, `samples.csv`, `predictions.csv`, fitted `.joblib` models,
`metrics.json` and `manifest.json` with input-manifest hashes, output hashes,
threshold, split, seed and limitations. Both source runs are verified through
Tam's independent handoff consumer before and after reading. Only load trusted
locally generated joblib files. Models need the same scikit-learn environment.

The full 15-corpus Reddit run is now available locally. See
[the reproduced pilot results](FORECAST-RESULTS.md) for source verification,
actual scores and class-support limitations. Generated artifacts remain outside Git.
