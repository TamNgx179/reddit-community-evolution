# Dataset distribution

This release includes the 15 original `*.corpus.zip` archives in `raw/` and historical processed datasets in `processed/`. Binary ZIP, Parquet and SQLite files use Git LFS. CSV tables and JSON metadata use regular Git. `DATASET-MANIFEST.json` records the size and SHA-256 of every distributed data file, plus the unpacked DuckDB database.

The raw archives contain Reddit discussion content and may include public usernames. They are not anonymized by putting them in LFS. Retain the upstream provenance and applicable terms when using or redistributing the corpus. `private/`, the HMAC key, local environments and generated `artifacts/` are excluded from this release. Do not publish keys or identity lookup tables.

## Download

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

## Restore the legacy database

`processed/all15-v1/merged.duckdb` exceeds GitHub Free's LFS per-file limit. Its byte-identical contents are distributed as `merged.duckdb.zip`. Extract it only if working with this historical import:

```powershell
python -m zipfile -e data/processed/all15-v1/merged.duckdb.zip data/processed/all15-v1
```

Compare the extracted file's SHA-256 with `unpacked_files` in `DATASET-MANIFEST.json`. The original local database was preserved during packaging. The current `reddit_sna prepare` pipeline reads `raw/` directly and does not require this DuckDB file or the historical processed tables.

## Reproduce the current pilot

The `all15-v1` and `moderatepolitics-v1/v2` directories are historical processed imports. They are not the canonical `reply-r-v3-order1` graph/detection/validation artifacts described in the research report. They must not be substituted for those runs merely because their filenames look similar.

After installing the project dependencies, build a new twelve-month train-only run from the downloaded raw archives:

```powershell
& .\.venv\Scripts\python.exe -m reddit_sna prepare --config configs/core.toml --start 2015-01 --end 2016-01 --run-id reddit-annual-reproduction-001
```

Run IDs are immutable: choose a new ID on every rebuild. In the pilot notebook, select this detection run through `DETECTION_RUN` or `REDDIT_DETECTION_RUN`, then restart the kernel and run all cells. The default replay ID refers to the original local research run, whose `artifacts/` are not part of this dataset release. See the main README for kernel setup and the report for evidence limits.
