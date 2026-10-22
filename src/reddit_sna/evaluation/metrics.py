
"""Evaluation metrics for community evolution predictions."""

from __future__ import annotations

import pandas as pd
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from reddit_sna.contracts import Event


LABELS = [event.value for event in Event]

KEY_COLUMNS = [
    "reference_id",
    "feature_month",
    "community_id",
    "label_month",
]

PREDICTION_COLUMNS = {
    *KEY_COLUMNS,
    "model",
    "y_true",
    "y_pred",
}

SPLIT_COLUMNS = {*KEY_COLUMNS, "split"}

METRIC_COLUMNS = [
    "model",
    "split",
    "n",
    "n_classes_present",
    "macro_f1",
    "macro_f1_six",
    "balanced_accuracy",
]

PER_CLASS_COLUMNS = [
    "model",
    "split",
    "label",
    "precision",
    "recall",
    "f1",
    "support",
]


def _validate_inputs(
    predictions: pd.DataFrame,
    split: pd.DataFrame,
) -> pd.DataFrame:
    """Validate predictions and attach their temporal split."""
    missing_predictions = PREDICTION_COLUMNS - set(predictions.columns)
    if missing_predictions:
        raise ValueError(
            f"Missing prediction columns: {sorted(missing_predictions)}"
        )

    missing_split = SPLIT_COLUMNS - set(split.columns)
    if missing_split:
        raise ValueError(
            f"Missing split columns: {sorted(missing_split)}"
        )

    if predictions.empty:
        raise ValueError("predictions must not be empty")

    if split.empty:
        raise ValueError("split must not be empty")

    pred = predictions[list(PREDICTION_COLUMNS)].copy()
    split_data = split[KEY_COLUMNS + ["split"]].copy()

    if pred.isna().any().any():
        raise ValueError("Prediction keys, model, y_true, and y_pred must not be missing")

    if split_data.isna().any().any():
        raise ValueError("Split keys and split must not contain missing values")

    if pred.duplicated(KEY_COLUMNS + ["model"]).any():
        raise ValueError("Found duplicate prediction rows for the same sample and model")

    if split_data.duplicated(KEY_COLUMNS).any():
        raise ValueError("Found duplicate sample keys in split")

    valid_splits = {"train", "validation", "test"}
    invalid_splits = set(split_data["split"].astype(str)) - valid_splits
    if invalid_splits:
        raise ValueError(f"Invalid split values: {sorted(invalid_splits)}")

    valid_true = set(pred["y_true"].astype(str)) - set(LABELS)
    valid_pred = set(pred["y_pred"].astype(str)) - set(LABELS)
    if valid_true or valid_pred:
        raise ValueError(
            f"Invalid event labels: y_true={sorted(valid_true)}, "
            f"y_pred={sorted(valid_pred)}"
        )

    empty_predictions = pred["y_pred"].astype(str).str.strip().eq("")
    if empty_predictions.any():
        raise ValueError("y_pred must not be empty")

    merged = pred.merge(
        split_data,
        on=KEY_COLUMNS,
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    unmatched = merged["_merge"] != "both"
    if unmatched.any():
        examples = merged.loc[unmatched, KEY_COLUMNS].head(3).to_dict("records")
        raise ValueError(
            f"Predictions contain sample keys missing from split: {examples}"
        )

    return merged.drop(columns="_merge")


def evaluate_predictions(
    predictions: pd.DataFrame,
    split: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Return overall metrics and per-class metrics for each model and split.

    macro_f1 averages only classes present in y_true.
    macro_f1_six averages across all six Event classes.
    """
    data = _validate_inputs(predictions, split)

    metric_rows = []
    per_class_rows = []

    for (model_name, split_name), group in data.groupby(
        ["model", "split"], sort=True
    ):
        truth = group["y_true"].astype(str)
        predicted = group["y_pred"].astype(str)
        present_labels = [label for label in LABELS if (truth == label).any()]

        f1_by_class = f1_score(
            truth,
            predicted,
            labels=LABELS,
            average=None,
            zero_division=0,
        )

        precision, recall, f1_values, supports = precision_recall_fscore_support(
            truth,
            predicted,
            labels=LABELS,
            zero_division=0,
        )

        f1_lookup = dict(zip(LABELS, f1_by_class))
        present_f1 = [f1_lookup[label] for label in present_labels]

        metric_rows.append({
            "model": str(model_name),
            "split": str(split_name),
            "n": int(len(group)),
            "n_classes_present": int(len(present_labels)),
            "macro_f1": float(sum(present_f1) / len(present_f1)),
            "macro_f1_six": float(sum(f1_by_class) / len(LABELS)),
            "balanced_accuracy": float(
                balanced_accuracy_score(truth, predicted)
            ),
        })

        for index, label in enumerate(LABELS):
            per_class_rows.append({
                "model": str(model_name),
                "split": str(split_name),
                "label": label,
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1_values[index]),
                "support": int(supports[index]),
            })

    return {
        "metrics": pd.DataFrame(metric_rows, columns=METRIC_COLUMNS),
        "per_class": pd.DataFrame(
            per_class_rows,
            columns=PER_CLASS_COLUMNS,
        ),
    }


def confusion_matrices(
    predictions: pd.DataFrame,
    split: pd.DataFrame,
) -> dict[tuple[str, str], pd.DataFrame]:
    """Return six-class confusion matrices keyed by (model, split)."""
    data = _validate_inputs(predictions, split)
    matrices: dict[tuple[str, str], pd.DataFrame] = {}

    for (model_name, split_name), group in data.groupby(
        ["model", "split"], sort=True
    ):
        matrix = confusion_matrix(
            group["y_true"].astype(str),
            group["y_pred"].astype(str),
            labels=LABELS,
        )
        matrices[(str(model_name), str(split_name))] = pd.DataFrame(
            matrix,
            index=pd.Index(LABELS, name="y_true"),
            columns=pd.Index(LABELS, name="y_pred"),
        )

    return matrices