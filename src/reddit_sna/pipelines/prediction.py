"""Prediction pipeline: synthetic community table -> split -> baselines -> evaluation.

Entry point:
    python -m reddit_sna.pipelines.prediction --config configs/prediction.toml --run-id prediction-demo-001

Ownership:
    Tram: _stage_table, _stage_baselines, main, run framework
    Lan Anh: _stage_evaluation (stub until Anh's branch is merged)

Data kind: synthetic -- not Reddit results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd

from reddit_sna.benchmarks.community_table import (
    TableParams,
    feature_catalog,
    generate_community_table,
    write_table,
)
from reddit_sna.config import ConfigError, RunConfig, load_config
from reddit_sna.contracts import Event, Prediction, SampleKey
from reddit_sna.models.logistic_regression import (
    B4Config,
    fit_logreg,
    predict_logreg,
    save_config,
    save_model,
)
from reddit_sna.models.majority_persistence import (
    fit_majority,
    predict_majority,
    predict_persistence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info() -> dict[str, str | None]:
    try:
        rev = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = subprocess.call(
            ["git", "diff", "--quiet"], stderr=subprocess.DEVNULL
        ) != 0
        return {"revision": rev, "dirty": dirty}
    except Exception:
        return {"revision": None, "dirty": None}


def _lib_versions() -> dict[str, str]:
    libs = {}
    for name in ("numpy", "pandas", "scikit-learn"):
        try:
            libs[name] = version(name)
        except Exception:
            libs[name] = "unknown"
    return libs


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Stage: table generation (Tram)
# ---------------------------------------------------------------------------

def _stage_table(run_dir: Path, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic community-month table and feature catalog."""
    params = TableParams()
    table = generate_community_table(seed=seed, params=params)
    catalog = feature_catalog()
    written = write_table(table, catalog, run_dir)
    print(f"  [table] Generated {len(table)} rows -> {written['samples.csv']}")
    return table, catalog


# ---------------------------------------------------------------------------
# Stage: baselines (Tram)
# ---------------------------------------------------------------------------

def _stage_baselines(
    run_dir: Path,
    table: pd.DataFrame,
    split: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    """Fit B1 (Majority, Persistence) and B4 (LogReg) on train; predict all labelled rows."""

    labelled = table[table["label"] != ""].copy()

    # Join split info
    split_key = ["reference_id", "feature_month", "community_id", "label_month"]
    merged = labelled.merge(split[split_key + ["split"]], on=split_key, how="left")

    train_rows = merged[merged["split"] == "train"]
    all_labelled = merged[merged["split"].notna()]  # train + validation + test

    # ---- B1 Majority ----
    majority_model = fit_majority(train_rows)
    maj_preds = predict_majority(majority_model, all_labelled)

    # ---- B1 Persistence ----
    per_preds = predict_persistence(majority_model, all_labelled)

    # ---- B4 Logistic Regression ----
    # ValueError (e.g. < 2 classes in train) propagates to caller — do NOT catch silently.
    logreg_model = fit_logreg(train_rows, seed=seed, config=B4Config())
    lr_preds = predict_logreg(logreg_model, all_labelled)
    save_config(B4Config(), logreg_model, run_dir)
    save_model(logreg_model, run_dir)

    # ---- Build predictions.csv ----
    key_cols = ["reference_id", "feature_month", "community_id", "label_month"]
    all_event_vals = [e.value for e in Event]
    proba_cols = [f"proba_{ev}" for ev in all_event_vals]

    pred_rows: list[dict] = []
    for model_name, preds_df in [
        ("B1_majority", maj_preds),
        ("B1_persistence", per_preds),
        ("B4_logreg", lr_preds),
    ]:
        # Include proba_* columns for B4 (they exist in predict_logreg output)
        merge_cols = ["reference_id", "feature_month", "community_id", "y_pred", "used_fallback"]
        if model_name == "B4_logreg":
            merge_cols += [c for c in proba_cols if c in preds_df.columns]

        tmp = all_labelled[key_cols].copy()
        tmp["y_true"] = all_labelled["label"].values
        tmp = tmp.merge(
            preds_df[merge_cols],
            on=["reference_id", "feature_month", "community_id"],
            how="left",
        )
        for _, row in tmp.iterrows():
            pred_row: dict[str, Any] = {
                "reference_id": row["reference_id"],
                "feature_month": row["feature_month"],
                "community_id": row["community_id"],
                "label_month": row["label_month"],
                "model": model_name,
                "y_true": row["y_true"],
                "y_pred": row.get("y_pred", ""),
                "used_fallback": row.get("used_fallback", False),
            }
            for ev in all_event_vals:
                col = f"proba_{ev}"
                pred_row[col] = row.get(col, None)
            pred_rows.append(pred_row)

    pred_cols = (
        key_cols + ["model", "y_true", "y_pred", "used_fallback"]
        + [f"proba_{ev}" for ev in all_event_vals]
    )
    pred_df = pd.DataFrame(pred_rows, columns=pred_cols)

    # Validate every (key, model) can construct a Prediction (non-empty y_pred)
    _validate_predictions(pred_df)

    _write_csv(run_dir / "predictions.csv", pred_rows, pred_cols)
    print(f"  [baselines] Wrote {len(pred_rows)} prediction rows -> predictions.csv")
    return pred_df


def _validate_predictions(pred_df: pd.DataFrame) -> None:
    """Check every (key, model) -> Prediction is constructable."""
    valid_events = {e.value for e in Event}
    for _, row in pred_df.iterrows():
        if not str(row["y_pred"]).strip():
            raise ValueError(f"Empty y_pred for row: {row.to_dict()}")
        if row["y_pred"] not in valid_events:
            raise ValueError(f"Invalid y_pred '{row['y_pred']}' not in Event")
        if row["y_true"] not in valid_events:
            raise ValueError(f"Invalid y_true '{row['y_true']}' not in Event")
        # Also verify SampleKey construction is valid
        SampleKey(
            reference_id=str(row["reference_id"]),
            feature_month=str(row["feature_month"]),
            community_id=str(row["community_id"]),
        )
        # And Prediction
        Prediction(
            key=SampleKey(
                reference_id=str(row["reference_id"]),
                feature_month=str(row["feature_month"]),
                community_id=str(row["community_id"]),
            ),
            label_month=str(row["label_month"]),
            model=str(row["model"]),
            y_true=Event(str(row["y_true"])),
            y_pred=Event(str(row["y_pred"])),
        )


# ---------------------------------------------------------------------------
# Stage: evaluation stub (Lan Anh owns _stage_evaluation)
# ---------------------------------------------------------------------------

def _stage_evaluation(run_dir: Path, table: pd.DataFrame,
                      split: pd.DataFrame, predictions: pd.DataFrame) -> None:
    """Stub: Lan Anh implements this stage in her branch.

    When Anh's branch is merged, replace this stub with the real call to:
        evaluation.splits.assign_temporal_split
        evaluation.sample_checks.check_samples / assert_samples_ok
        evaluation.metrics.evaluate_predictions / confusion_matrices
    """
    # Stub writes a placeholder note so the pipeline run completes
    notes = (
        "# Evaluation\n\n"
        "Stub: Lan Anh's _stage_evaluation not yet merged.\n"
        "data_kind: synthetic\n"
        "table_schema: prediction-table-v1\n"
    )
    (run_dir / "evaluation_notes.md").write_text(notes, encoding="utf-8")
    print("  [evaluation] stub wrote evaluation_notes.md (Lan Anh's stage pending merge)")


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(config: RunConfig) -> Path:
    """Execute the prediction pipeline with a fresh exclusive run directory."""
    from reddit_sna.artifacts import create_run_directory

    run_dir = create_run_directory(config)
    start_time = datetime.now(timezone.utc)
    stage_status: dict[str, str] = {}

    try:
        # Stage 1: generate table
        table, catalog = _stage_table(run_dir, config.seed)
        stage_status["table"] = "complete"

        # Stage 2: TEMPORARY basic split (replace by Anh's assign_temporal_split once merged)
        split = _basic_temporal_split(table)
        _write_csv(run_dir / "split.csv",
                   split.to_dict(orient="records"),
                   list(split.columns))
        stage_status["split"] = "complete"

        # Stage 3: baselines (Tram)
        predictions = _stage_baselines(run_dir, table, split, config.seed)
        stage_status["baselines"] = "complete"

        # Stage 4: evaluation (Anh)
        _stage_evaluation(run_dir, table, split, predictions)
        stage_status["evaluation"] = "complete_stub"

    except Exception as exc:
        stage_status.setdefault("failed_at", str(exc))
        _write_manifest(run_dir, config, start_time, stage_status, status="failed")
        raise

    # Evaluation stage is still a stub (Lan Anh's branch not yet merged).
    # Use "complete_through_baselines" per ARCHITECTURE policy — never claim
    # "complete" when a downstream stage is unfinished.
    _write_manifest(run_dir, config, start_time, stage_status,
                    status="complete_through_baselines")
    print(f"\n[prediction] Pipeline complete_through_baselines -> {run_dir}")
    return run_dir


def _basic_temporal_split(table: pd.DataFrame) -> pd.DataFrame:
    """Basic temporal split: train 2015-02..2016-12, val 2017-01..2017-06, test 2017-07..2017-12.

    Drops rows with empty label (last feature month).
    Used until Anh's evaluation/splits.py is merged.
    """
    labelled = table[table["label"] != ""].copy()
    labelled = labelled.reset_index(drop=True)

    def assign(lm: str) -> str:
        if lm <= "2016-12":
            return "train"
        elif lm <= "2017-06":
            return "validation"
        else:
            return "test"

    labelled["split"] = labelled["label_month"].apply(assign)
    key_cols = ["reference_id", "feature_month", "community_id", "label_month", "split"]
    return labelled[key_cols].copy()


def _write_manifest(run_dir: Path, config: RunConfig, start_time: datetime,
                    stage_status: dict, status: str) -> None:
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    # Collect artifact hashes
    artifact_hashes = {}
    for p in sorted(run_dir.iterdir()):
        if p.is_file() and p.name != "manifest.json":
            artifact_hashes[p.name] = _sha256(p)

    manifest: dict[str, Any] = {
        "status": status,
        "data_kind": "synthetic",
        "table_schema": "prediction-table-v1",
        "config": config.to_dict(),
        "seed": config.seed,
        "git": _git_info(),
        "python_version": platform.python_version(),
        "libraries": _lib_versions(),
        "stage_status": stage_status,
        "elapsed_seconds": elapsed,
        "peak_memory_mb": None,
        "artifact_hashes": artifact_hashes,
        "unimplemented": [
            "B2_random_forest (Phuc)", "B5_gradient_boosting (Phuc)",
            "HeTCo (Thanh)", "real Reddit features (Thanh)",
            "Lan_Anh_evaluation_stage",
        ],
    }

    with (run_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Prediction pipeline: synthetic table -> baselines -> evaluation"
    )
    parser.add_argument("--config", required=True, help="Path to prediction.toml")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config), run_id=args.run_id)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        run(config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"Pipeline error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()