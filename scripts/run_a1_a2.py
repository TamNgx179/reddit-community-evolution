
import argparse
from pathlib import Path
import sys
import json
from datetime import datetime, timezone

import pandas as pd

# Cho phép import package trong src layout.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reddit_sna.evaluation.diagnostics import forecast_tables, size_band


# ============================================================
# 1. INPUT / OUTPUT
# ============================================================

parser = argparse.ArgumentParser(
    description="Generate A1/A2 final-window evaluation tables."
)

parser.add_argument(
    "--handoff",
    type=Path,
    required=True,
    help="Path to the frozen F1 handoff directory.",
)

parser.add_argument(
    "--out",
    type=Path,
    required=True,
    help="New output directory. Existing directories are not overwritten.",
)

args = parser.parse_args()

HANDOFF = args.handoff.expanduser().resolve()
OUT = args.out.expanduser().resolve()

PRED_PATH = HANDOFF / "export" / "predictions_final.csv"
FEATURE_PATH = HANDOFF / "export" / "features_all.csv"
LABEL_PATH = HANDOFF / "export" / "labels_status_all.csv"

KEY = [
    "reference_id",
    "feature_month",
    "community_id",
    "label_month",
    "label_reference_id",
]

FEATURE_KEY = [
    "reference_id",
    "feature_month",
    "community_id",
]

CLASSES = [
    "stable",
    "grow",
    "shrink",
    "merge",
    "split",
    "dissolve",
]


# ============================================================
# 2. CHECK INPUT FILES
# ============================================================

for path in [PRED_PATH, FEATURE_PATH, LABEL_PATH]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input: {path}")

if OUT.exists():
    raise FileExistsError(
        f"Output folder already exists: {OUT}\n"
        "Choose another run directory to avoid overwriting."
    )

OUT.mkdir(parents=True)


# ============================================================
# 3. READ ONLY REQUIRED COLUMNS
# ============================================================

print("[1/5] Reading inputs...")

pred = pd.read_csv(
    PRED_PATH,
    usecols=KEY + [
        "model", "seed", "window",
        "y_true", "y_pred", "fallback",
    ],
    dtype={k: "string" for k in KEY},
    low_memory=False,
)

features = pd.read_csv(
    FEATURE_PATH,
    usecols=FEATURE_KEY + [
        "size",
        "density",
        "community_age",
        "history_missing",
        "context_history_missing",
    ],
    dtype={k: "string" for k in FEATURE_KEY},
    low_memory=False,
)

labels = pd.read_csv(
    LABEL_PATH,
    usecols=KEY + ["label", "status"],
    dtype={k: "string" for k in KEY},
    low_memory=False,
)


# ============================================================
# 4. VALIDATE KEYS AND PREDICTION SCHEDULE
# ============================================================

print("[2/5] Validating prediction schedule...")

if set(pred["window"].dropna().unique()) != {"final"}:
    raise ValueError("Expected final-window predictions only.")

if pred.duplicated(KEY + ["model", "seed"]).any():
    raise ValueError("Duplicate sample × model × seed predictions.")

if features.duplicated(FEATURE_KEY).any():
    raise ValueError("Duplicate feature keys.")

if labels.duplicated(KEY).any():
    raise ValueError("Duplicate label sample keys.")

models = sorted(pred["model"].dropna().unique())
seeds = sorted(
    pd.to_numeric(pred["seed"], errors="raise").astype(int).unique()
)

if len(models) != 19:
    raise ValueError(f"Expected 19 models, got {len(models)}.")

if seeds != [42, 43, 44]:
    raise ValueError(f"Unexpected seeds: {seeds}")

run_counts = pred.groupby(["model", "seed"]).size()

if not (run_counts == 1269).all():
    raise ValueError(
        "Every model-seed must contain 1,269 predictions.\n"
        f"Unexpected counts:\n{run_counts[run_counts != 1269]}"
    )

unique_samples = pred[KEY].drop_duplicates()

if len(unique_samples) != 1269:
    raise ValueError(
        f"Expected 1,269 unique final samples, got {len(unique_samples)}."
    )


# ============================================================
# 5. VERIFY Y_TRUE AGAINST THE RESOLVED LABEL EXPORT
# ============================================================

print("[3/5] Checking labels and feature joins...")

check = pred.merge(
    labels,
    on=KEY,
    how="left",
    validate="many_to_one",
    indicator=True,
)

if not check["_merge"].eq("both").all():
    raise ValueError("Some predictions do not match the label export.")

if not check["status"].eq("resolved").all():
    raise ValueError("Non-resolved rows found in final predictions.")

if not check["y_true"].eq(check["label"]).all():
    raise ValueError("y_true does not match the resolved label.")

feature_check = unique_samples.merge(
    features,
    on=FEATURE_KEY,
    how="left",
    validate="many_to_one",
    indicator=True,
)

if not feature_check["_merge"].eq("both").all():
    raise ValueError("Some final samples lack feature metadata.")

if feature_check["size"].isna().any():
    raise ValueError("Missing community size.")

# Ensure required numeric values are valid.
features["size"] = pd.to_numeric(features["size"], errors="raise")
features["history_missing"] = pd.to_numeric(
    features["history_missing"], errors="coerce"
)
features["context_history_missing"] = pd.to_numeric(
    features["context_history_missing"], errors="coerce"
)

pred["seed"] = pd.to_numeric(pred["seed"], errors="raise").astype(int)
pred["fallback"] = pd.to_numeric(
    pred["fallback"], errors="raise"
).astype(int)

if pred[["y_true", "y_pred", "fallback"]].isna().any().any():
    raise ValueError("Missing prediction values.")

if not set(pred["y_true"]).issubset(CLASSES):
    raise ValueError("Unexpected y_true class.")

if not set(pred["y_pred"]).issubset(CLASSES):
    raise ValueError("Unexpected y_pred class.")


# ============================================================
# 6. CALL THE COMMITTED DIAGNOSTIC MODULE
# ============================================================

print("[4/5] Running forecast_tables()...")

prediction_records = pred.to_dict(orient="records")
feature_records = features.to_dict(orient="records")

metrics, classes, confusion = forecast_tables(
    prediction_records,
    feature_records,
)

metrics_df = pd.DataFrame(metrics)
classes_df = pd.DataFrame(classes)
confusion_df = pd.DataFrame(confusion)

if metrics_df.empty or classes_df.empty or confusion_df.empty:
    raise ValueError("Diagnostic module returned empty results.")

# Every stratum must have six class rows.
class_counts = classes_df.groupby(
    ["window", "model", "seed", "axis", "stratum"]
).size()

if not (class_counts == 6).all():
    raise ValueError("Some strata do not contain all six classes.")

# Every confusion matrix must have 36 cells.
confusion_counts = confusion_df.groupby(
    ["window", "model", "seed", "axis", "stratum"]
).size()

if not (confusion_counts == 36).all():
    raise ValueError("Some confusion matrices do not contain 36 cells.")


# ============================================================
# 7. EXPORT A1
# ============================================================

print("[5/5] Exporting A1 and A2...")

# A1: monthly metrics.
metrics_df.query("axis == 'month'").to_csv(
    OUT / "A1_monthly_macro_summary.csv",
    index=False,
)

classes_df.query("axis == 'month'").to_csv(
    OUT / "A1_monthly_class_metrics.csv",
    index=False,
)

confusion_df.query("axis == 'month'").to_csv(
    OUT / "A1_monthly_confusion.csv",
    index=False,
)

# A1: overall metrics.
metrics_df.query("axis == 'all'").to_csv(
    OUT / "A1_overall_macro_summary.csv",
    index=False,
)

classes_df.query("axis == 'all'").to_csv(
    OUT / "A1_overall_class_metrics.csv",
    index=False,
)

confusion_df.query("axis == 'all'").to_csv(
    OUT / "A1_overall_confusion.csv",
    index=False,
)


# ============================================================
# 8. EXPORT A2
# ============================================================

# size: singleton, 2, 3-4, 5-20, >20
# lineage_history: missing / available
# member_activity_history: available / missing_or_not_recorded
# size_history: combined size × lineage-history strata

A2_AXES = [
    "size",
    "lineage_history",
    "member_activity_history",
    "size_history",
]

metrics_df[
    metrics_df["axis"].isin(A2_AXES)
].to_csv(
    OUT / "A2_stratified_macro_summary.csv",
    index=False,
)

classes_df[
    classes_df["axis"].isin(A2_AXES)
].to_csv(
    OUT / "A2_stratified_class_metrics.csv",
    index=False,
)

confusion_df[
    confusion_df["axis"].isin(A2_AXES)
].to_csv(
    OUT / "A2_stratified_confusion.csv",
    index=False,
)

# Also export separate files for easier inspection.
for axis in A2_AXES:
    metrics_df.query("axis == @axis").to_csv(
        OUT / f"A2_{axis}_macro_summary.csv",
        index=False,
    )

    classes_df.query("axis == @axis").to_csv(
        OUT / f"A2_{axis}_class_metrics.csv",
        index=False,
    )

    confusion_df.query("axis == @axis").to_csv(
        OUT / f"A2_{axis}_confusion.csv",
        index=False,
    )


# ============================================================
# 9. AUDIT AND README
# ============================================================

audit = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "prediction_rows": int(len(pred)),
    "unique_final_samples": int(len(unique_samples)),
    "models": models,
    "seeds": seeds,
    "rows_per_model_seed": 1269,
    "all_labels_resolved": True,
    "all_y_true_match_label_export": True,
    "all_features_matched": True,
    "fixed_classes": CLASSES,
    "metric_strata": sorted(metrics_df["axis"].unique().tolist()),
    "label_month_min": str(pred["label_month"].min()),
    "label_month_max": str(pred["label_month"].max()),
    "note": (
        "Final-window predictions only. Unresolved and censored cases "
        "are excluded from predictive metrics and remain in coverage analysis."
    ),
}

(OUT / "validation_audit.json").write_text(
    json.dumps(
        audit,
        indent=2,
        ensure_ascii=False,
        default=lambda x: x.item() if hasattr(x, "item") else str(x),
    ),
    encoding="utf-8",
)

readme = """
A1 + A2 — FULL-STUDY FINAL-WINDOW DIAGNOSTICS

Source:
- export/predictions_final.csv
- export/features_all.csv
- export/labels_status_all.csv

Implementation:
- Uses reddit_sna.evaluation.diagnostics.forecast_tables().
- No model is fitted or refitted.
- Each model and seed remains separate.
- Uses label_month for monthly evaluation.
- Fixed six-class Macro-F1; absent classes receive zero_division=0 behavior.
- Confusion matrix: rows are true labels, columns are predicted labels.

A1:
- Monthly and overall Macro-F1.
- Per-class precision, recall, F1 and support.
- Confusion matrices by month and overall.

A2:
- Size strata.
- Lineage-history strata.
- Member-activity-history strata.
- Joint size × lineage-history strata.

Important:
- size_band includes singleton separately from the four requested bands.
- history_missing is lineage history, not member-activity history.
- Seeds are repeat runs, not independent communities.
- Unresolved and censored targets are not converted into event labels.
- Final predictions cover 1,269 unique samples, not all 7,490 resolved samples.
- Validation candidate predictions are not pooled with final predictions.
"""

(OUT / "README_A1_A2.txt").write_text(
    readme.strip() + "\n",
    encoding="utf-8",
)

print("\nDONE")
print("Output:", OUT)
print("Prediction rows:", len(pred))
print("Unique samples:", len(unique_samples))
print("Models:", len(models))
print("Seeds:", seeds)
print("A1/A2 strata:", sorted(metrics_df["axis"].unique()))