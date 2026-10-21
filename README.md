# Reddit Community Evolution

Research package for detecting, tracking and forecasting Reddit **user communities**. Subreddits are activity contexts, not ground-truth community labels.

The core baseline runs **raw ZIPs → audited normalization → monthly reply graphs → Independent Leiden → GED adaptation → current/past-only features → temporal Majority/Logistic Regression → verified evaluation and figures**. HeTCo, full original GED, multislice/consensus and the other pair demos remain planned. The generic `run` entrypoint remains unfinished; use `week1` for the complete baseline.

## Quick start

Python **3.11+**, Git LFS and a terminal at the repository root are required. In PowerShell:

```powershell
git lfs install
git lfs pull --include="data/raw/*.zip" --exclude=""
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,forecast,notebook]'
& .\.venv\Scripts\python.exe -m reddit_sna week1 --config configs/core.toml --run-id week1-demo
```

Use a new run ID each time. The full fifteen-corpus January–December 2015 rebuild takes minutes and writes local immutable outputs under `artifacts/core/week1-demo-input/` and `artifacts/core/week1-demo/{forecast,report}/`. Linux/macOS use `.venv/bin/python`. See the [runbook](docs/RUNBOOK.md) for kernel setup, preparation-only commands, explicit replay, tests and troubleshooting.

## Notebooks

- [Preparation and SNA diagnostics](notebooks/core/01_reddit_pilot.ipynb): ten code cells and fourteen figure families.
- [Tracking and forecast evaluation](notebooks/core/02_core_forecast.ipynb): seven code cells and six figure families, including both model confusion matrices.
- [Midterm research](notebooks/core/03_midterm_research.ipynb): seven code cells and seven figures for context features, ablations, main/rolling comparisons and uncertainty.
- [Synthetic detection and tracking](notebooks/detection_tracking/01_synthetic_demo.ipynb): fourteen code cells and eight figures, separating detector errors from tracking errors.
- [Synthetic forecasting baselines](notebooks/prediction/01_baseline_demo.ipynb): six code cells and five figures for class support, baseline scores and confusion matrices.
- [Synthetic evaluation analysis](notebooks/prediction/02_evaluation_analysis.ipynb): executed consistency checks, split/metric tables and test confusion-matrix tables for the independently generated synthetic run. This notebook displays tables, not plots.

All six demonstration and analysis notebooks contain executed snapshots with code and results visible on GitHub. Figures are embedded in the five notebooks that generate plots. The evaluation analysis notebook displays its original tables. To run them, select this repository's `.venv` kernel in VS Code/Jupyter and restart/run all. GitHub provides a static preview. The three `00_research_plan.ipynb` files remain unfinished templates.

## Documentation

| Document | Read it for |
|---|---|
| [Methods and architecture](docs/METHODS.md) | Module boundaries, graph/identity semantics, tracking, causal features, split rules and CSV contracts |
| [Runbook](docs/RUNBOOK.md) | Data download, environment/kernel setup, pipeline/notebook commands, verification and offline handoff |
| [Results and evidence](docs/RESULTS.md) | Current acceptance, scores/support, limitations, historical run provenance and presentation outline |
| [Label review](docs/LABEL_REVIEW.md) | Blinded sampling, independent annotation and adjudication |
| [Eight-week assignment](PHAN-CONG-SNA-8-TUAN.md) | Individual responsibilities and pair milestones |

## Repository layout

```text
configs/                 Independent core, detection/tracking and prediction configs
src/reddit_sna/          Functional modules shared by CLI and notebooks
notebooks/              core/, detection_tracking/, prediction/
tests/                  Synthetic unit/integration cases
docs/                   Four technical guides listed above
experiments/            Draft protocols, experiment/ablation/feature/literature records
reports/                Structured claim/evidence and contribution tables
data/                   Authorized raw/historical dataset release; private identities stay local
artifacts/              Local immutable outputs per pipeline/run ID
```

Week-one pairs use independent inputs/outputs; stable reusable logic belongs in `src/reddit_sna`. Features at t cannot read t+1, splits use whole label-month groups and preprocessing fits training rows only. Different cohort or label references must not be joined silently.

The current baseline passed **161 tests without skips** and a full real raw-to-evaluation run. Scores remain descriptive: labels are tracker-derived, the test stable class is absent, dissolve dominates and unresolved transitions are excluded explicitly. Human review and an untouched confirmatory period remain pending. The [results](docs/RESULTS.md) retain these limits alongside scores; passing tests and arranging source cannot guarantee paper novelty or a grade.

The owner authorized original datasets through Git LFS and the executed demonstration and analysis notebook snapshots. Keep private keys, identity lookups, annotation cases and standalone runtime artifacts local. Draft `experiments/` records describe planned research and are not runtime-enforced evidence.
