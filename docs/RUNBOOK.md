# Runbook

Commands run from the repository root. Use a new immutable output ID for each run. For definitions and CSV contracts see [methods](METHODS.md); for measured evidence see [results](RESULTS.md).

The current midterm narrative is the [integrated report](../reports/WEEK1_REPORT.md).
The supplementary component study uses eight fixed configurations with the
original primary LR settings. It does not add headline baselines or replace
the primary using exposed outcomes:

```powershell
reddit-sna component-study --protocol configs/components.toml --original artifacts/temporal/activity-study-001 --external artifacts/confirmation/political-cohort-001 --output artifacts/components/controlled-new
```

Use a new output path. Historical samples, source manifests and prepared blinded
review payloads are prerequisites. The output contains per-sample predictions,
matched full-minus-control differences, temporal uncertainty and blank review
forms. These exposed-period analyses are separate from a future frozen cohort
and actual independent human assessment. Reproduction of the original primary
and A1 final predictions is required before component results are interpreted.

HeTCo v1 runs on the exact samples of a completed `research` run. It takes
about 12 minutes on the 2015 pilot:

```powershell
reddit-sna research --protocol configs/midterm.toml --preparation-run artifacts/core/reddit-2015-reproduced-v1 --forecast-run artifacts/core/forecast-ged-history-v3 --run-id midterm-thanh-001
reddit-sna hetco --research-run artifacts/research/midterm-thanh-001 --preparation-run artifacts/core/reddit-2015-reproduced-v1 --run-id hetco-v1-002
python -c "from reddit_sna.reporting.hetco import export_figures; export_figures('artifacts/hetco/hetco-v1-002', 'reports/figures/hetco-v1-002')"
reddit-sna hetco --research-run artifacts/research/midterm-thanh-001 --preparation-run artifacts/core/reddit-2015-reproduced-v1 --run-id hetco-v2-001 --model HeTCo_v1 --model HeTCo_v2 --model A7v2_mean_pool
```

The v2 run selects its configuration on the inner origins, then fits. It takes
about 10 minutes.

After a completed original/external temporal study, run the development-only audit:

```powershell
reddit-sna audit-continuity --protocol configs/continuity_audit.toml --study artifacts/temporal/activity-study-001 --output artifacts/validation/continuity-original-002
reddit-sna audit-continuity --protocol configs/continuity_audit.toml --study artifacts/confirmation/political-cohort-001 --output artifacts/validation/continuity-external-002
```

These paths identify the runs displayed in the notebook. Existing destinations
are refused. To reproduce, choose new output IDs and update the notebook's local
reader paths. Source stores and memberships are local prerequisites; outputs
saved in the committed notebook allow GitHub viewing without those stores.
The audit observes only pre-2018 data and changes no model, target or feature.

## Predeclared new-cohort replication

`configs/prospective.toml` fixes Anarchism, Libertarian and GreenParty and their
checked Cornell source URLs and compressed sizes. The 35-field candidate drops
only record/reply growth. Five transferred baselines, the original 37-field
model, no-D and a matched flat 35-field control remain in the comparison.
There is no search over the new final outcomes.

Run these stages in order from the repository root, using one new output ID:

```powershell
foreach ($stage in @('acquire', 'develop', 'fit', 'evaluate', 'review')) {
    & .\.venv\Scripts\python.exe -m reddit_sna prospective-study --protocol configs/prospective.toml --root artifacts/prospective/ideological-reproduction --stage $stage
    if ($LASTEXITCODE -ne 0) { throw "Prospective stage failed: $stage" }
}
```

The declaration precedes acquisition. Only pre-2018 graphs, targets and features
are prepared before fitting. All models, source and sample hashes freeze before
the evaluation stage extends metadata and constructs 2018 targets. An unchanged
development prefix is mandatory. Completed stage outputs are immutable and a
failed attempt is preserved. Do not edit scientific source between fit and
evaluate. Resource journals record sampled process-tree RSS, disk and exit status.

The `review` stage prepares a separate development structural panel beside the
study directory. A supplied technical assessment can be validated using
`reddit-sna assess-structure --panel <panel> --submission <actual-submission.json>
--output <new-output>`. This tool validates evidence and explicitly non-human
provenance. It does not manufacture independent human review. For actual reviewer
submissions use the separate procedure in `LABEL_REVIEW.md`.

The executed core notebook shows the measured run `artifacts/prospective/ideological-001`.
When reproducing under a different ID, update its reader path after completing
the stages. Saved notebook outputs support GitHub viewing. Executing its readers
requires the original, component and prospective artifacts referenced by the
notebook. Raw new-cohort archives and private assessment cases are kept local.

## Contents

- [Fresh checkout](#fresh-checkout)
- [Dataset distribution](#dataset-distribution)
- [Preparation stages](#preparation-stages)
- [Notebooks and kernels](#notebooks-and-kernels)
- [Forecast consumption](#forecast-consumption)
- [Verification](#verification)

The baseline is Reddit input → audited normalization → monthly R → Independent Leiden → GED adaptation → current/past-only features and next-month pseudo-labels → temporal baselines → verified evaluation. This pair does not need another pair's generated outputs. HeTCo, full original GED, T-layer and multislice/consensus are later research work.

## Fresh checkout

Use Python 3.11+ and Git LFS. In PowerShell at the repository root:

```powershell
git lfs install
git lfs pull --include="data/raw/*.zip" --exclude=""
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.[graph,forecast,notebook]'
& .\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name reddit-sna --display-name 'Reddit SNA (.venv)'
& .\.venv\Scripts\python.exe -m reddit_sna week1 --config configs/core.toml --run-id week1-demo
```

`week1-demo` must be new. A raw rebuild writes an immutable `week1-demo-input` preparation run and a separate `week1-demo/` delivery with forecast, report and a completion manifest. This is the full all15 January–December 2015 train-only demo; the forecast split is by label month at October 2015. Do not change that split after seeing scores. Linux/macOS use `.venv/bin/python`.

The command verifies inputs and hashes, delegates to the same prepare/forecast code as the separate CLI commands, then exports six forecast figure families as PNG/SVG. No model pickle is loaded by reporting. A failed run is marked failed; choose another ID after inspecting the error. Large raw reconstruction takes minutes and requires substantial local disk space. `data/processed/` contains historical imports and is not the input to this path.

## Replay verified preparation inputs

To skip raw normalization/detection, supply both existing run paths explicitly:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna week1 --config configs/core.toml --run-id week1-replay-001 --graph-run artifacts/core/reddit-2015-ordered-graphs-v1 --detection-run artifacts/core/reddit-2015-ordered-detection-v1
```

These two example paths refer to the original workstation. On a new machine use the preparation run created by your own raw command for **both** flags, or explicit linked graph/detection runs. Replay is not a fresh raw reconstruction. It produces new forecast/report outputs without changing its sources. The generic `run --config ...` remains unfinished; use `week1`, `prepare` and `forecast` for the implemented stages.

Current preparation metadata says `forecast_status=not_run_by_preparation`, meaning that this stage stops at membership. Historical immutable producer manifests may retain the old `not_implemented` placeholder; it describes the producer's original scope, not the current package's forecasting support. Those historical records are preserved rather than rewritten.

## Show the notebook

1. Open `notebooks/core/02_core_forecast.ipynb` in VS Code/Jupyter.
2. Select the repository's `.venv` interpreter, restart and run all. A terminal activation alone does not change the kernel.
3. Default selection is `artifacts/core/week1-demo/forecast`, created by the raw command. To select the replay example, set `REDDIT_FORECAST_RUN=core/week1-replay-001/forecast` in the kernel environment before launch, or change the explicit selector in the setup cell.
4. The notebook verifies the manifest, labels/features/sample joins and metrics before displaying six-class support, excluded transitions, model comparison, per-class metrics, both confusion matrices, monthly diagnostics, development folds and actual prediction errors.

The reviewed saved notebook is a static snapshot of an actual run, and GitHub renders its code and embedded figures. It cannot run cells on GitHub. The preparation notebook's fourteen figures are separate; use it for upstream SNA diagnostics rather than treating them as forecasting evaluation.

An existing forecast can be plotted separately without retraining:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna forecast-report --run artifacts/core/week1-demo/forecast --output artifacts/core/forecast-report-002
```

Set `REDDIT_FORECAST_EXPORT=core/forecast-report-003` to request a new export while replaying the notebook. No export is written by default. Both export paths are immutable and must stay under project artifacts.

## Dataset distribution

This release includes the 15 original `*.corpus.zip` archives in `data/raw/` and historical processed datasets in `data/processed/`. Binary ZIP, Parquet and SQLite files use Git LFS. CSV tables and JSON metadata use regular Git. `data/DATASET-MANIFEST.json` records the size and SHA-256 of every distributed data file, plus the unpacked DuckDB database.

The raw archives contain Reddit discussion content and may include public usernames. They are not anonymized by putting them in LFS. Retain the upstream provenance and applicable terms when using or redistributing the corpus. `data/private/`, the HMAC key, local environments and generated `artifacts/` are excluded from this release. Do not publish keys or identity lookup tables.

### Download

Install [Git LFS](https://git-lfs.com/), then run at the repository root:

```powershell
git lfs install
git lfs pull
git lfs fsck
```

Without LFS, binary files may be small pointer files instead of usable datasets. To download only the raw input needed by the current pipeline:

```powershell
git lfs pull --include="data/raw/*.zip" --exclude=""
```

The full distribution is several GB. Each collaborator's download consumes the repository owner's shared LFS bandwidth allowance; review [GitHub LFS storage and bandwidth billing](https://docs.github.com/en/billing/concepts/product-billing/git-lfs) before repeatedly downloading all files. This repository does not configure billing or purchase additional capacity.

### Restore the legacy database

`data/processed/all15-v1/merged.duckdb` exceeds GitHub Free's LFS per-file limit. Its byte-identical contents are distributed as `merged.duckdb.zip`. Extract it only if working with this historical import:

```powershell
python -m zipfile -e data/processed/all15-v1/merged.duckdb.zip data/processed/all15-v1
```

Compare the extracted file's SHA-256 with `unpacked_files` in `data/DATASET-MANIFEST.json`. The original local database was preserved during packaging. The current `reddit_sna prepare` pipeline reads `data/raw/` directly and does not require this DuckDB file or the historical processed tables.

### Reproduce the current pilot

The `all15-v1` and `moderatepolitics-v1/v2` directories are historical processed imports. They are not the canonical `reply-r-v3-order1` graph/detection/validation artifacts described in the research report. They must not be substituted for those runs merely because their filenames look similar.

After installing the project dependencies, build a new twelve-month train-only run from the downloaded raw archives:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --start 2015-01 --end 2016-01 --run-id reddit-annual-reproduction-001
```

Run IDs are immutable: choose a new ID on every rebuild. In the pilot notebook, select this detection run through `DETECTION_RUN` or `REDDIT_DETECTION_RUN`, then restart the kernel and run all cells. The default replay ID refers to the original local research run, whose `artifacts/` are not part of this dataset release. See the main README for kernel setup and the report for evidence limits.

## Preparation stages

Preparation stages can also run separately (these examples default to January–March and stop before forecasting):

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage audit --run-id reddit-audit-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage normalize --run-id reddit-normalize-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage snapshots --source-run artifacts/core/reddit-normalize-001 --run-id reddit-graphs-001
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --stage detect --source-run artifacts/core/reddit-graphs-001 --run-id reddit-leiden-001
```

Normalization audits raw inputs again. Downstream stages verify completed source manifests and artifact hashes before writing fresh outputs. Omitted month flags inherit the source interval. Explicit detection bounds must match the entire snapshot cohort; build a new snapshot run first for a subset. `--start` is inclusive and `--end` exclusive, inside official train.

## Notebooks and kernels

Open [01_reddit_pilot.ipynb](../notebooks/core/01_reddit_pilot.ipynb) for preparation/detection, then [02_core_forecast.ipynb](../notebooks/core/02_core_forecast.ipynb) for verified tracking/forecast results. Follow [the complete week-one demo](RUNBOOK.md) to create the required artifacts from a fresh checkout.

1. Install dependencies using the commands above.
2. Register a project-local kernel if needed:

   ```powershell
   & .\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name reddit-sna --display-name 'Reddit SNA (.venv)'
   ```

3. In VS Code, enable the Python and Jupyter extensions. Choose **Select Kernel > Python Environments > this repository's `.venv\Scripts\python.exe`**. A terminal activation alone does not change the notebook kernel. The first cell prints the actual interpreter.
4. Choose **Restart Kernel > Run All**. Never modify `sys.path` or copy source into notebooks. If imports fail, install into the printed interpreter and select/restart that kernel.

Default **REPLAY** reads `reddit-2015-ordered-detection-v1` and follows its recorded graph/normalization ancestors, verifying checksums, periods, identities and totals. Edit `DETECTION_RUN` or set `REDDIT_DETECTION_RUN` to select another local run. If no run exists, run the CLI above and select its ID, or set `REBUILD=True` in the notebook to process raw inputs using the same API. Rebuild is slower; replay does not scan raw data again. Use `REDDIT_SNA_PROJECT` only when the kernel's working directory is outside the repository tree.

The notebook renders fourteen figure families: the original eight cover data scope, corpus-month support, graph volume, coverage, exclusive reply outcomes, community sizes, partition diagnostics and a labeled display sample of the network. Six additional figures cover components/density, degree/strength, interaction concentration, predeclared corpus contexts, gamma sensitivity and edge perturbation. All use verified actual artifacts. PNG/SVG exports and a source-linked manifest go to a fresh `artifacts/core/reddit-pilot-figures-<timestamp>/` folder. The pilot notebook includes a reviewed execution snapshot with all ten code cells, tables and fourteen figures visible on GitHub. GitHub renders a static preview; rerun cells in VS Code or Jupyter using the project kernel. Additional executed copies and standalone figure artifacts stay local. Stable replay/plot code lives in `reporting/`, not in duplicated notebook cells. For automated fresh-kernel execution, `nbclient` is included in the notebook extra; configure its working directory as the repository and its kernel as this `.venv` interpreter.

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

The automated handoff consumer uses only public CSV/manifest contracts and standard-library code, independently of producer modules. It checks canonical membership keys, reference/month, endpoint coverage and hashes. It proves interface readiness, not acceptance by a partner, collaborator permissions or working downstream forecasting. Twelve months provide eleven potential transitions, not guaranteed label/class support or a valid forecast split. The implemented `forecast` stage and `week1` demo now consume this handoff through persisted predictions and verified evaluation. See the current forecast notebook and handoff guide; earlier producer-only evidence remains historical.

New snapshots use **reply-r-v3-order1**. A real aligned experiment exposed an ordering problem in historical v2: January-March graphs agreed across quarter/annual normalization scopes, but partitions changed because ordinal user allocation changed vertex and edge insertion order. New `node_order.csv` keys hash the minimum authored record identifier available **through the snapshot month**, and detection canonicalizes node and edge indices. The sidecar is hash-bound to graph/reference identity; raw author names are never stored in it. Old v2 artifacts remain separate and unchanged. This is an engineering reproducibility correction, not a new community-detection method or a guarantee of social validity.

On a fresh checkout `prepare` generates the ordered protocol directly. The documented raw command creates a new all-stage run; set notebook `DETECTION_RUN` to that run ID and select matching validation IDs. Development replay defaults point to the separately verified immutable ordered runs. A graph/membership handoff now includes `node_order.csv` alongside R/directed_R/users; the canonical membership CSV schema stays unchanged.

## Forecast consumption

For a new checkout, use [the complete week-one demo](RUNBOOK.md). Its default raw command creates `artifacts/core/week1-demo-input` and `artifacts/core/week1-demo/forecast`. The examples below preserve the original workstation's reproduction IDs; replace them with the exact runs you created. The focused forecast notebook and `forecast-report` command consume this same schema without loading model pickles.

```powershell
python -m pip install -e ".[forecast]"
python -m reddit_sna forecast --graph-run artifacts/core/reddit-2015-reproduced-v1 --detection-run artifacts/core/reddit-2015-reproduced-v1 --output artifacts/core/forecast-ged-history-v3 --test-start 2015-10 --tracker ged --history
```

The output ID must be new. Split boundary and fixed tracker parameters are not
selected by held-out scores. Input manifests/hashes and source code hashes must
remain unchanged throughout the run. Model environment versions are recorded.

Recipients can verify and read tables without importing sklearn or unpickling:

```python
from pathlib import Path
from reddit_sna.reporting.forecast_handoff import read_handoff
delivery = read_handoff(Path("artifacts/core/forecast-ged-history-v3"))
features = delivery["features"]
labels = delivery["labels"]
samples = delivery["samples"]
feature_order = delivery["manifest"]["features"]
label_reference_id = delivery["manifest"]["label_reference_id"]
```

The consumer verifies every hash, exact CSV column order, unique keys, feature
availability, complete source-label coverage, eligibility, joins, held-out sample
coverage and confusion matrices/macro-F1 recomputed independently from predictions.
The current consumer additionally cross-checks plotted per-class metrics, balanced accuracy, class/month support, exclusion reasons, development-fold boundaries/support and saved error examples. Its return value includes verified `metrics`, `quality`, `predictions`, `errors` and `development_folds` for reporting, alongside the original tables.

The Jaccard fallback can be selected by omitting `--tracker ged --history` from the forecast command. It uses a different label reference and eligible population; see [methods](METHODS.md#jaccard-fallback-semantics). To obtain raw archives from the original Cornell index instead of the Git LFS release, run `python scripts/download_reddit.py --download`; without that flag it only lists URLs and sizes.

## Verification

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m pip wheel --no-deps . --wheel-dir dist
```

Validate the regular wheel in a separate environment as well as the editable package. The current executed verification is recorded in [results](RESULTS.md#final-delivery-verification). Tests use temporary synthetic inputs and do not supply social ground truth.

## Cases covered

| Stage | Checks |
|---|---|
| Tracker | All six events, many-to-many split precedence, exact Jaccard threshold boundary, births excluded from source samples, no successor, empty snapshots, invalid empty/overlapping communities |
| Tracker invariance | 100 seeded random partition pairs checked against independent pairwise overlap/event calculations; community renaming and insertion-order invariance |
| Features | Hand-calculated internal and boundary weights, density, singleton/empty cases, renamed users, reversed edge order/direction; reject duplicate edges, missing endpoint membership and mixed months |
| Samples | Unique reference/month/community keys; reject mixed references, duplicate samples, unknown labels, nonconsecutive label months, NaN/infinite/nonnumeric features |
| Temporal model | Train/test nonempty, exact label-month boundary, whole months held together, year boundary, scaler trained on training rows only, fitted coefficients unchanged by held-out feature/label changes |
| Baselines | Single-class Majority fallback, multiclass Logistic Regression, fixed seeds, repeated execution, six-class metric order and independent confusion counts |
| Handoff | Combined run and separately linked graph/detection runs, integrity corruption, source manifest changed during read, missing input and calendar gap rejection |
| End-to-end | Empty middle month retained as dissolve rather than joined across; no invented final-month sample; expected feature values and labels recovered from synthetic archives |
| Output | Saved models reload, hashes match, output cannot escape artifacts or overwrite prior runs, simulated CSV write error records failed manifest and preserves source |

Additional upstream handoff tests in the full suite check duplicate membership
users, missing endpoints, wrong references, altered schema and unverified inputs.

Additional current checks verify GED ambiguity/history, future-append invariance, independently recomputed per-class metrics/coverage/errors/folds, immutable report exports, raw/replay orchestration and blinded review. Run the offline packaging check with the rest of the integration suite.

## Offline forecast handoff

```powershell
& .\.venv\Scripts\python.exe scripts/package_forecast.py --run artifacts/core/week1-demo/forecast --output artifacts/core/forecast-handoff-001.zip
```

The local ZIP includes verified forecast outputs and all six navigation documents in their repository layout. Document-to-document links work after extraction. Notebook links require the repository checkout; notebooks and preparation artifacts are not included. It excludes raw datasets, private identities and annotation packages. Create the matching local preparation artifacts before replaying notebook or raw-demo commands.

## Environment constraints and interpretation

Run the full synthetic suite using `python -m unittest discover -s tests -v`. See `METHODS.md#forecast-handoff-schema-2` for CSV contracts and `RESULTS.md#annual-ged-delivery-provenance` for historical descriptive scores. Model versions and source hashes belong to each actual run. `constraints-week1.txt` records the tested Windows Python 3.13.3 environment: optionally install with `python -m pip install -c constraints-week1.txt -e ".[graph,forecast,notebook]"`. This is a version constraints snapshot, not a cross-platform hash lock; on another Python/platform, verify compatibility and retain actual environment versions in the run manifest.

Read `summary.json`, forecast `quality.json` and `metrics.json` together. Keep zero-support events and the excluded population visible. Scores measure prediction of tracker-derived pseudo-labels, not independently established social events. Previously inspected 2015 held-out scores remain descriptive. Do not compare Jaccard/GED scores as a controlled improvement because their eligible populations and label references differ.

Use `LABEL_REVIEW.md` to prepare independent review and the [integrated report](../reports/WEEK1_REPORT.md#113-research-decision) for the current follow-up priorities. Executable study protocols are in `configs/`; `RESULTS.md#presentation-outline` retains the historical pair presentation outline. Software evidence does not establish annotation completion, attendance, accepted collaborator invitations or paper novelty.
