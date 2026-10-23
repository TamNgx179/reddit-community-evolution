# Reddit Community Evolution

## Source acknowledgments

Research using this project should acknowledge the [ConvoKit subreddit corpus](https://convokit.cornell.edu/documentation/subreddit.html) and its original data source, together with:

- J. P. Chang, C. Chiam, L. Fu, A. Wang, J. Zhang, and C. Danescu-Niculescu-Mizil, “ConvoKit: A Toolkit for the Analysis of Conversations,” *Proceedings of SIGDIAL*, 2020. [Paper](https://www.cs.cornell.edu/~cristian/ConvoKit_Demo_Paper_files/convokit-demo-paper.pdf).
- J. Baumgartner, S. Zannettou, B. Keegan, M. Squire, and J. Blackburn, “The Pushshift Reddit Dataset,” *Proceedings of ICWSM*, vol. 14, pp. 830–839, 2020. [Paper](https://doi.org/10.1609/icwsm.v14i1.7347).

These references provide attribution; they do not assign a new license to Reddit content. Preserve applicable copyright and permission notices when redistributing third-party software.

Research package for detecting, tracking and forecasting Reddit **user communities**. Subreddits are activity contexts, not ground-truth community labels.

The core baseline runs **raw ZIPs → audited normalization → monthly reply graphs → Independent Leiden → GED adaptation → current/past-only features → temporal forecasting → verified evaluation and figures**. Independent detection/tracking and prediction demos are also implemented. Full HeTCo, original GED and multislice/consensus remain planned. The generic `run` entrypoint remains unfinished; use `week1` for the core baseline or `temporal-study` for the full chronological experiment.

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

Start with **05_temporal_activity_study.ipynb** for the current compact experiment. The other completed notebooks retain the original week-one diagnostics and independent pair demonstrations.

- [Preparation and SNA diagnostics](notebooks/core/01_reddit_pilot.ipynb): ten code cells and fourteen figure families.
- [Tracking and forecast evaluation](notebooks/core/02_core_forecast.ipynb): seven code cells and six figure families, including both model confusion matrices.
- [Midterm research](notebooks/core/03_midterm_research.ipynb): seven code cells and seven figures for context features, ablations, main/rolling comparisons and uncertainty.
- [Full temporal activity study](notebooks/core/05_temporal_activity_study.ipynb): executed measurement audit, frozen comparisons and seven real figures across the 2015–2018 study. The [integrated report](reports/WEEK1_REPORT.md) explains the problem, graph, labels, protocol and measured findings in English.
- [Synthetic detection and tracking](notebooks/detection_tracking/01_synthetic_demo.ipynb): fourteen code cells and eight figures, separating detector errors from tracking errors.
- [Synthetic forecasting baselines](notebooks/prediction/01_baseline_demo.ipynb): six code cells and five figures for class support, baseline scores and confusion matrices.
- [Synthetic evaluation analysis](notebooks/prediction/02_evaluation_analysis.ipynb): executed consistency checks, split/metric tables and test confusion-matrix tables for the independently generated synthetic run. This notebook displays tables, not plots.

All seven demonstration, analysis and research notebooks listed above contain executed snapshots with code and results. Six contain embedded figures; the evaluation analysis notebook displays its original tables. To run them, select this repository's `.venv` kernel in VS Code/Jupyter and restart/run all. The research readers require their completed local runs, documented below. GitHub provides a static preview.

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

The full temporal study completed a real raw-to-evaluation run with an independent check of 57 model/seed groups. Its frozen primary method reached six-class Macro-F1 **0.4117**, versus **0.3880** for the strongest expanded nonlinear reference. The original validation-champion comparison (HGB static, **0.3728**) has paired interval **[0.0056, 0.0744]**; this interval must not be attributed to the stronger expanded reference. This is evidence on the defined operational target. Labels are tracker-derived, stable has only four final-period cases, dissolve dominates, and unresolved transitions are excluded explicitly. Human review and unseen confirmation remain pending. The [integrated report](reports/WEEK1_REPORT.md) contains the new results; [historical results](docs/RESULTS.md) retain the earlier pilot's separate scope. Software checks and a baseline win do not establish paper novelty or a grade.

The owner authorized original datasets through Git LFS and the executed demonstration and analysis notebook snapshots. Keep private keys, identity lookups, annotation cases and standalone runtime artifacts local. Draft `experiments/` records describe planned research and are not runtime-enforced evidence.
# Full temporal activity study

The versioned `configs/temporal_study.toml` separates training labels
(February 2015–June 2017), whole-month validation (July–December 2017), and a
frozen-model evaluation (January–September 2018). Earlier 2015 results remain
development evidence. Historical exposure to later forecast labels is not
independently certified; do not call a new date range an unseen confirmation.

Install `.[graph,research,notebook]` in the project virtual environment, then run
these stages in order. Repeating a stage reuses only hash-verified complete
work; failed attempts and original input archives are preserved.

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna temporal-study --protocol configs/temporal_study.toml --root artifacts/temporal/activity-study-five-baselines-001 --stage normalize-development
& .\.venv\Scripts\python.exe -m reddit_sna temporal-study --protocol configs/temporal_study.toml --root artifacts/temporal/activity-study-five-baselines-001 --stage develop
& .\.venv\Scripts\python.exe -m reddit_sna temporal-study --protocol configs/temporal_study.toml --root artifacts/temporal/activity-study-five-baselines-001 --stage select
& .\.venv\Scripts\python.exe -m reddit_sna temporal-study --protocol configs/temporal_study.toml --root artifacts/temporal/activity-study-five-baselines-001 --stage evaluate
& .\.venv\Scripts\python.exe -m reddit_sna temporal-study --protocol configs/temporal_study.toml --root artifacts/temporal/activity-study-five-baselines-001 --stage report
```

The first stage streams metadata before 2018. `develop` builds monthly reply
graphs, Leiden memberships, causal features, operational labels and blinded
review forms. `select` uses equal candidate budgets and freezes models before
`evaluate` may prepare final-period snapshots or read their targets. A resource
monitor records sampled process-tree RSS, wall time and disk limits. It stops
rather than silently truncating the study.

The current protocol retains **five baselines**: Majority, Persistence, flat
Logistic Regression with all dynamic features, hierarchical static HGB, and
hierarchical dynamic HGB. The original proposed hierarchical dynamic LR and one
matched no-dynamics ablation bring the total to **seven configurations**. Four
tuned families use eight settings and six validation origins each (192
configuration-fold evaluations; two-head models fit up to two estimators each).

The executed notebook presents the original frozen study through this seven-row
view. All nineteen original configurations remain preserved locally and are
audited before projection. HGB dynamic was originally an alternative architecture
and is now explicitly reported as a strong nonlinear reference. This reporting
change happened after evaluation; it is not a new independent experiment. The
original primary, settings, predictions and champion comparison are unchanged.
The English [midterm report](reports/WEEK1_REPORT.md) separately reports the
strongest expanded reference and its exploratory paired interval.
Use the new root above for future schema3 runs, preserving the original frozen
root. No model search on the final-period labels is performed by this view.

The proposed hierarchy predicts disappearance and then the conditional event;
flat, static-feature and matched no-dynamics controls test whether it adds
value. Six-class Macro-F1, class support, exclusions and negative findings are
retained. Review forms do not establish human validation. Neither a baseline
win nor scientific novelty is guaranteed by the implementation.

Use `notebooks/core/05_temporal_activity_study.ipynb` after the real evaluation
completes. It verifies saved predictions without unpickling models and displays
actual results and figures. New stores, memberships, review cases, models and
resource logs remain local. The report stage creates a local integrated report
draft for review before replacing the canonical group report or Google Docs.
