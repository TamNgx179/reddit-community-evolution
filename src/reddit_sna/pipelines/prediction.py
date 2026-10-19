"""Prediction pipeline: synthetic community table -> split -> baselines -> evaluation.

Entry point:
    python -m reddit_sna.pipelines.prediction --config configs/prediction.toml --run-id prediction-demo-001

Ownership:
    Tram: _stage_table, _stage_baselines, main, run framework
    Lan Anh: _stage_evaluation, split and sample checks (evaluation/ package)

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

from reddit_sna.evaluation.metrics import (
    confusion_matrices,
    evaluate_predictions,
)
from reddit_sna.evaluation.sample_checks import (
    assert_samples_ok,
    check_samples,
)
from reddit_sna.evaluation.splits import (
    assign_temporal_split,
    summarize_split,
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
# Stage: evaluation (Lan Anh owns _stage_evaluation)
# ---------------------------------------------------------------------------

def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a Markdown table without extra dependencies."""

    def escape_cell(value: object) -> str:
        text = str(value)
        text = text.replace("\\", "\\\\")
        text = text.replace("|", "\\|")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\n", "<br>")
        return text

    columns = [escape_cell(column) for column in df.columns]
    rows = [
        [escape_cell(value) for value in row]
        for row in df.itertuples(index=False, name=None)
    ]

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    lines.extend(
        "| " + " | ".join(row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def _stage_evaluation(
    run_dir: Path,
    table: pd.DataFrame,
    catalog: pd.DataFrame,
    split: pd.DataFrame,
    predictions: pd.DataFrame,
) -> None:
    """Validate samples and write temporal evaluation outputs."""
    assert_samples_ok(check_samples(table, catalog, split))

    # Count rows excluded because they have no label.
    unlabeled_dropped = int(
        (table["label"].isna() | (table["label"] == "")).sum()
    )

    # Reuse the split created in Stage 2.
    temporal_split = split.copy()

    # Validate all predictions against the canonical split.
    # Metrics are calculated separately for each available split.
    evaluation_predictions = predictions.copy()

    results = evaluate_predictions(evaluation_predictions, temporal_split)
    matrices = confusion_matrices(evaluation_predictions, temporal_split)

    metrics = results["metrics"]
    per_class = results["per_class"]

    _write_csv(
        run_dir / "metrics.csv",
        metrics.to_dict(orient="records"),
        list(metrics.columns),
    )
    _write_csv(
        run_dir / "per_class.csv",
        per_class.to_dict(orient="records"),
        list(per_class.columns),
    )

    for (model_name, split_name), matrix in matrices.items():
        safe_model_name = str(model_name).replace("/", "_").replace("\\", "_")
        matrix_path = run_dir / f"confusion_{safe_model_name}_{split_name}.csv"
        matrix.to_csv(matrix_path, index=True, index_label="y_true")

    # Document classes with no true examples in each model/split group.
    missing_class_rows = per_class.loc[per_class["support"] == 0]
    if missing_class_rows.empty:
        missing_class_text = "No classes have zero true support."
    else:
        missing_class_text = _dataframe_to_markdown(
            missing_class_rows[["model", "split", "label", "support"]]
        )

    notes = [
        "# Evaluation notes",
        "",
        "- data_kind: synthetic",
        "- table_schema: prediction-table-v1",
        f"- labelled_samples: {len(temporal_split)}",
        f"- unlabeled_dropped: {unlabeled_dropped}",
        f"- prediction_rows: {len(evaluation_predictions)}",
        "- macro_f1: average F1 over classes present in y_true; zero_division=0",
        "- macro_f1_six: average F1 over all six Event classes; zero_division=0",
        "- balanced_accuracy: mean recall over classes present in y_true",
        "- Predictions are matched to the temporal split by sample key.",
        "- Rows without a matching split key are rejected.",
        "",
        "## Classes with zero true support",
        "",
        missing_class_text,
        "",
        "## Metrics",
        "",
        _dataframe_to_markdown(metrics),
        "",
        "## Per-class metrics",
        "",
        _dataframe_to_markdown(per_class),
        "",
        "## Confusion matrices",
        "",
        "Each `confusion_<model>_<split>.csv` contains a six-class matrix.",
        "",
    ]

    (run_dir / "evaluation_notes.md").write_text(
        "\n".join(notes),
        encoding="utf-8",
    )

    print(
        "  [evaluation] completed: "
        f"{len(evaluation_predictions)} prediction rows, "
        f"{len(metrics)} model/split metric rows"
    )

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

        # Stage 2: temporal split for evaluation
        assert_samples_ok(check_samples(table, catalog))

        split = assign_temporal_split(table)

        assert_samples_ok(check_samples(table, catalog, split))
        split_summary = summarize_split(table, split)

        _write_csv(
            run_dir / "split.csv",
            split.to_dict(orient="records"),
            list(split.columns),
        )
        _write_csv(
            run_dir / "split_summary.csv",
            split_summary.to_dict(orient="records"),
            list(split_summary.columns),
        )
        stage_status["split"] = "complete"

        # Stage 3: baselines (Tram)
        predictions = _stage_baselines(run_dir, table, split, config.seed)
        stage_status["baselines"] = "complete"

        # Stage 4: evaluation (Anh)
        _stage_evaluation(run_dir, table, catalog, split, predictions)
        stage_status["evaluation"] = "complete"

    except Exception as exc:
        stage_status.setdefault("failed_at", str(exc))
        _write_manifest(run_dir, config, start_time, stage_status, status="failed")
        raise

    # Evaluation is implemented; other planned models/features remain unfinished.
    # Keep the overall status aligned with the project's completion policy.
    _write_manifest(run_dir, config, start_time, stage_status,
                    status="complete_through_baselines")
    print(f"\n[prediction] Pipeline complete_through_baselines -> {run_dir}")
    return run_dir


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