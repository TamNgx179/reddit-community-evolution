# Reddit Community Evolution

Research package for detecting, tracking and forecasting Reddit **user communities**. Subreddits are activity contexts, not ground-truth community labels.

The core baseline runs **raw ZIPs → audited normalization → monthly reply graphs → Independent Leiden → GED adaptation → current/past-only features → temporal Majority/Logistic Regression → verified evaluation and figures**. The synthetic detection/tracking and table-prediction demos are also implemented. A separate `research` command implements **HeTCo-v0**, a preliminary context/history feature forecaster with matched B5 and ablations on the inspected 2015 reference. Full final HeTCo, original GED and multislice/consensus remain planned. The generic `run` entrypoint remains unfinished; use `week1` for the complete baseline.

## Quick start

Python **3.11+**, Git LFS and a terminal at the repository root are required. In PowerShell:

```powershell
git lfs install
git lfs pull --include="data/raw/*.zip" --exclude=""
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,forecast,evaluation,prediction,notebook]'
& .\.venv\Scripts\python.exe -m reddit_sna week1 --config configs/core.toml --run-id week1-demo
```

Use a new run ID each time. The full fifteen-corpus January–December 2015 rebuild takes minutes and writes local immutable outputs under `artifacts/core/week1-demo-input/` and `artifacts/core/week1-demo/{forecast,report}/`. Linux/macOS use `.venv/bin/python`. See the [runbook](docs/RUNBOOK.md) for kernel setup, preparation-only commands, explicit replay, tests and troubleshooting.

## Notebooks

- [Preparation and SNA diagnostics](notebooks/core/01_reddit_pilot.ipynb): ten code cells and fourteen figure families.
- [Tracking and forecast evaluation](notebooks/core/02_core_forecast.ipynb): seven code cells and six figure families, including both model confusion matrices.
- [Midterm research](notebooks/core/03_midterm_research.ipynb): verified baseline/proposed/ablation comparisons, monthly/class diagnostics and explicitly limited exploratory uncertainty. See the [midterm runbook](docs/RUNBOOK.md#midterm-research-explicit-inputs-and-a-frozen-development-protocol).

Both contain reviewed executed snapshots with code, results and charts visible on GitHub. To run them, select this repository's `.venv` kernel in VS Code/Jupyter and restart/run all. GitHub provides a static preview. The three `00_research_plan.ipynb` files remain unfinished planning templates. [Synthetic detection/tracking](notebooks/detection_tracking/01_synthetic_demo.ipynb) and [synthetic prediction](notebooks/prediction/01_baseline_demo.ipynb) provide executable demos after their input runs are built; their reviewed execution copies remain local.

## Documentation

| Document | Read it for |
|---|---|
| [Methods and architecture](docs/METHODS.md) | Module boundaries, graph/identity semantics, tracking, causal features, split rules and CSV contracts |
| [Runbook](docs/RUNBOOK.md) | Data download, environment/kernel setup, pipeline/notebook commands, verification and offline handoff |
| [Results and evidence](docs/RESULTS.md) | Current acceptance, scores/support, limitations, historical run provenance and presentation outline |
| [Label review](docs/LABEL_REVIEW.md) | Blinded sampling, independent annotation and adjudication |
| [Group week-one report](reports/WEEK1_REPORT.md) | Six contributions, three independently reproduced demos, results, errors and limits |
| [Eight-week assignment](PHAN-CONG-SNA-8-TUAN.md) | Individual responsibilities and pair milestones |

## Repository layout

```text
configs/                 Independent core, detection/tracking and prediction configs
src/reddit_sna/          Functional modules shared by CLI and notebooks
notebooks/              core/, detection_tracking/, prediction/
tests/                  Synthetic unit/integration cases
docs/                   Four technical guides listed above
experiments/            Draft protocols, experiment/ablation/feature/literature records
reports/                One complete group report: WEEK1_REPORT.md
data/                   Authorized raw/historical dataset release; private identities stay local
artifacts/              Local immutable outputs per pipeline/run ID
```

Week-one pairs use independent inputs/outputs; stable reusable logic belongs in `src/reddit_sna`. Features at t cannot read t+1, splits use whole label-month groups and preprocessing fits training rows only. Different cohort or label references must not be joined silently.

The earlier core baseline passed **161 tests without skips** and a full real raw-to-evaluation run. Current combined integration verification and all three reproduction commands are recorded in the [group report](reports/WEEK1_REPORT.md). Scores remain descriptive: labels are tracker-derived, the test stable class is absent, dissolve dominates and unresolved transitions are excluded explicitly. Human review and an untouched confirmatory period remain pending. The [results](docs/RESULTS.md) retain these limits alongside scores; passing tests and arranging source cannot guarantee paper novelty or a grade.

The owner authorized original datasets through Git LFS and the two reviewed notebook snapshots. Keep private keys, identity lookups, annotation cases and standalone runtime artifacts local. Draft `experiments/` records describe planned research and are not runtime-enforced evidence.
