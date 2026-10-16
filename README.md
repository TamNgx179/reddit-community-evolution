# Reddit Community Evolution

Research package for detecting, tracking and forecasting changes in Reddit **user communities**. Subreddits are activity contexts, not ground-truth community labels. The implemented `prepare` path is ZIP audit → metadata normalization → monthly reply graphs → Independent Leiden. Tracking, features, forecasting and the other pair demos remain unimplemented; `run` exits with code 3 rather than inventing results.

## Install and run

Python **3.11+** is required. In PowerShell at the repository root:

First download the binary inputs with `git lfs install` and `git lfs pull`. See [dataset distribution](data/README.md) for selective download, checksums, the compressed legacy database and reproduction instructions.

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,notebook]'
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --run-id reddit-pilot-001
```

Each run ID must be new. This scans all 15 ZIPs without extracting/modifying them and runs the January–March 2015 train-only pilot. Outputs are local under `artifacts/core/<run_id>/`. Use `--corpus moderatepolitics` for an explicitly labeled subset smoke test. Linux/macOS use `.venv/bin/python`. Dependencies are declared in `pyproject.toml`; manifests record installed versions.

Stages can also run separately:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage audit --run-id reddit-audit-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage normalize --run-id reddit-normalize-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage snapshots --source-run artifacts/core/reddit-normalize-001 --run-id reddit-graphs-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage detect --source-run artifacts/core/reddit-graphs-001 --run-id reddit-leiden-001
```

Normalization audits raw inputs again. Downstream stages verify completed source manifests and artifact hashes before writing fresh outputs. Omitted month flags inherit the source interval. Explicit detection bounds must match the entire snapshot cohort; build a new snapshot run first for a subset. `--start` is inclusive and `--end` exclusive, inside official train.

## Run the notebook

Open [01_reddit_pilot.ipynb](notebooks/core/01_reddit_pilot.ipynb), the executable pilot. The three `00_research_plan.ipynb` files are templates and deliberately raise `NotImplementedError`.

1. Install dependencies using the commands above.
2. Register a project-local kernel if needed:

   ```powershell
   & .\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name reddit-sna --display-name 'Reddit SNA (.venv)'
   ```

3. In VS Code, enable the Python and Jupyter extensions. Choose **Select Kernel > Python Environments > this repository's `.venv\Scripts\python.exe`**. A terminal activation alone does not change the notebook kernel. The first cell prints the actual interpreter.
4. Choose **Restart Kernel > Run All**. Never modify `sys.path` or copy source into notebooks. If imports fail, install into the printed interpreter and select/restart that kernel.

Default **REPLAY** reads `reddit-2015-ordered-detection-v1` and follows its recorded graph/normalization ancestors, verifying checksums, periods, identities and totals. Edit `DETECTION_RUN` or set `REDDIT_DETECTION_RUN` to select another local run. If no run exists, run the CLI above and select its ID, or set `REBUILD=True` in the notebook to process raw inputs using the same API. Rebuild is slower; replay does not scan raw data again. Use `REDDIT_SNA_PROJECT` only when the kernel's working directory is outside the repository tree.

The notebook renders fourteen figure families: the original eight cover data scope, corpus-month support, graph volume, coverage, exclusive reply outcomes, community sizes, partition diagnostics and a labeled display sample of the network. Six additional figures cover components/density, degree/strength, interaction concentration, predeclared corpus contexts, gamma sensitivity and edge perturbation. All use verified actual artifacts. PNG/SVG exports and a source-linked manifest go to a fresh `artifacts/core/reddit-pilot-figures-<timestamp>/` folder. The pilot notebook includes a reviewed execution snapshot with all ten code cells, tables and fourteen figures visible on GitHub. GitHub renders a static preview; rerun cells in VS Code or Jupyter using the project kernel. Additional executed copies and standalone figure artifacts stay local. Stable replay/plot code lives in `reporting/`, not in duplicated notebook cells. For automated fresh-kernel execution, `nbclient` is included in the notebook extra; configure its working directory as the repository and its kernel as this `.venv` interpreter.

## Research semantics and limitations

Reply direction is child author → parent author, using child time and requiring parent time ≤ child time. R sums both directions, omits self-replies and excludes unknown/deleted/removed/AutoModerator authors. Other bots are not comprehensively identified. Pre-pilot metadata supports parent lookup; future rows are excluded before allocating pseudonymous user IDs. IDs are valid only within one normalized run; pseudonyms do not guarantee anonymity.

Only users with reply edges receive memberships. Coverage distinguishes active authors, endpoints, parent-only endpoints, observed unions and isolates. Corpus-month audit includes zero-support cells and mutually exclusive reply outcomes summing to comments. Legacy incidence counters can overlap; unique corpus author counts cannot be added as unique network users.

Independent Leiden uses weighted RBConfiguration, gamma 1, seeds 0/1/2 and convergence, independently per month. The first seed is canonical. Modularity measures graph quality and seed ARI measures repeatability, neither social validity nor prediction accuracy. Empty graphs have no fabricated quality. Community names are local to each month.

Graph references bind protocol and cohort contents; membership references additionally bind identity scope, detector version, gamma and seed. Adding a month changes cohort identity; per-month hashes distinguish that from past graph changes. Legacy inputs receive a distinct protocol/reference. Do not join mismatched references automatically. `evaluation.causality.compare_causal_prefix` requires explicit bijective identity alignment and compares past graphs/partitions up to a cutoff; it does not validate unfinished tracking or forecasting.

The supplied grading policy allocates A1/A2 50% each and requires paper potential for maximum project credit. Architecture and passing software tests alone cannot establish novelty or a 9–10 grade. Three-month diagnostics are preparation evidence, not H1–H3 results. See [pilot report](reports/REDDIT-PILOT.md) and [architecture](ARCHITECTURE.md) for evidence limits and next experiments.

## Structure and independent pair demos

```text
configs/                 One TOML per independent pipeline
notebooks/               core/, detection_tracking/, prediction/
src/reddit_sna/
  data/                  Archive audit and normalized SQLite metadata
  graphs/                Reply projection, provenance and corpus audit
  detection/             Independent Leiden; temporal/consensus planned
  reporting/             Verified replay and descriptive figure generation
  tracking/              Planned community links, lineage and events
  features/              Planned cutoff-safe network/context/history features
  models/                Planned prediction baselines and proposed model
  evaluation/            Causal-prefix diagnostics; forecasting metrics planned
  benchmarks/            Planned controlled synthetic generators
  pipelines/             Preparation and three independent demo entrypoints
  config.py              Strict TOML and path validation
  contracts.py           Shared records, identifiers, months and events
  artifacts.py           Exclusive run reservation and initial provenance
tests/                   Synthetic unit/integration cases
experiments/             Draft study, experiment/ablation/feature/literature records
reports/                 Selected research reports and evidence templates
```

| Pipeline | Independent input and intended output | Config |
|---|---|---|
| `core` | Reddit → communities → tracking/features → forecasting evaluation | `configs/core.toml` |
| `detection-tracking` | Synthetic dynamic networks → detection/tracking evaluation | `configs/detection_tracking.toml` |
| `prediction` | Synthetic community-month tables → temporal baselines/evaluation | `configs/prediction.toml` |

Pairs share contracts and reusable modules, not generated inputs/outputs during week one. Individual ownership remains in the administrative [eight-week assignment](PHAN-CONG-SNA-8-TUAN.md). Source filenames describe functions, not people. Promote stable reusable/testable notebook prototypes into the corresponding package module; do not create a parallel code tree per pair or person.

## Configuration, outputs and verification

All TOML paths, including `project_root`, resolve relative to the TOML directory. `check` validates configuration/paths without reading the corpus or creating research outputs. Core needs an existing Reddit input folder; synthetic configs do not depend on Reddit. `run` remains unfinished. Exit codes are 0 for successful commands, 2 for input/config/path errors and 3 for unimplemented research pipelines. CLI streams are UTF-8, including Unicode filesystem paths.

Keep existing raw/processed/private data unchanged. The explicitly authorized [dataset release](data/README.md) publishes original raw archives and historical processed imports through Git LFS and regular Git metadata. Private keys, private identity lookup files, standalone runtime artifacts and unreviewed notebook outputs remain local; the pilot notebook includes the explicitly authorized reviewed execution snapshot. Runs cannot overwrite previous runs, overlap inputs or write into `data/`. A `started` manifest is not completion. Preparation records input/output/config/source hashes, Git revision and tracked dirty state, dependency versions, stage status and wall time. Peak memory is not measured and remains null. `complete_through_detection` does not mean forecasting completed.

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir dist
```

Tests use temporary synthetic data. Validate an installed wheel in a separate environment as well as the editable package. Work on feature branches, combine implementation and corresponding tests in each commit, and review staged product paths explicitly. Draft `experiments/` records are not runtime-enforced protocols; claim/evidence and contribution templates must reflect actual work. New algorithms belong in functional modules with behavior tests and explicit dependencies; no empty file for every planned algorithm is needed.

## Week-one research validation

The preparation path now has an explicit validation command:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --start 2015-01 --end 2016-01 --run-id reddit-pilot-2015-v1
& .\.venv\Scripts\python.exe -m reddit_sna.reporting.validation --project . --detection-run reddit-pilot-2015-v1 --output-id reddit-2015-validation-v1
& .\.venv\Scripts\python.exe -m reddit_sna.reporting.validation --project . --detection-run reddit-pilot-2015-v1 --output-id reddit-quarter-validation-v1 --sensitivity
```

Run IDs must be new. These commands rebuild January-December 2015 inside train, analyze full observed-user graphs and validate public handoff contracts. The final command runs the fixed January-March sensitivity schedule, while verifying the chosen source cohort. On the development workstation the immutable ordered quarter-sensitivity run references `reddit-quarter-ordered-detection-v1`, and annual replay selects `reddit-2015-ordered-detection-v1`; the notebook verifies and prints this distinction. Never join their ordinal user IDs or references. To reproduce that exact quarter cohort from scratch, first run `prepare` with `--start 2015-01 --end 2015-04` and select its new run ID for sensitivity.

Validation produces `network_analysis.json`, `handoff.json` and optionally `sensitivity.json`, with source hashes, environment, fixed schedule, elapsed time and completion/failure state. Peak native memory is not measured. Repeated IDs never overwrite results. The main notebook uses `REDDIT_DETECTION_RUN`, `REDDIT_ANALYSIS_RUN` and `REDDIT_SENSITIVITY_RUN` to choose explicit sources and exports fourteen figure families with validation provenance.

Graph diagnostics retain observed isolates in degree/strength/component denominators. Top-1% strength concentration uses ceil(1% of observed users) and total incident strength, which is twice total reply-event weight. Context analysis attributes replies to the child's corpus; user sets overlap. Predeclared contexts are AskALiberal, moderatepolitics and PoliticalDiscussion. Sensitivity uses gamma 0.5/1/2, detector seeds 0/1/2 and floor(5% of unique undirected edges) dropped with seeds 100/101/102. Remaining weights are unchanged; common-user ARI is accompanied by endpoint support retention. Constant or insufficient partitions have undefined informative ARI. Neither stability nor modularity is a selection rule or social ground-truth accuracy.

The automated handoff consumer uses only public CSV/manifest contracts and standard-library code, independently of producer modules. It checks canonical membership keys, reference/month, endpoint coverage and hashes. It proves interface readiness, not acceptance by a partner, collaborator permissions or working downstream forecasting. Twelve months provide eleven potential transitions, not guaranteed label/class support or a valid forecast split. The complete pair demo still needs the partner's tracker/features/model/evaluation.

New snapshots use **reply-r-v3-order1**. A real aligned experiment exposed an ordering problem in historical v2: January-March graphs agreed across quarter/annual normalization scopes, but partitions changed because ordinal user allocation changed vertex and edge insertion order. New `node_order.csv` keys hash the minimum authored record identifier available **through the snapshot month**, and detection canonicalizes node and edge indices. The sidecar is hash-bound to graph/reference identity; raw author names are never stored in it. Old v2 artifacts remain separate and unchanged. This is an engineering reproducibility correction, not a new community-detection method or a guarantee of social validity.

On a fresh checkout `prepare` generates the ordered protocol directly. The documented raw command creates a new all-stage run; set notebook `DETECTION_RUN` to that run ID and select matching validation IDs. Development replay defaults point to the separately verified immutable ordered runs. A graph/membership handoff now includes `node_order.csv` alongside R/directed_R/users; the canonical membership CSV schema stays unchanged.
