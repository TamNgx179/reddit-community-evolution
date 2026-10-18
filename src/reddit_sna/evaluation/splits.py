
"""Temporal train/validation/test splits for prediction samples."""

from __future__ import annotations

import pandas as pd

from reddit_sna.contracts import Event, next_month


SPLIT_COLUMNS = [
    "reference_id",
    "feature_month",
    "community_id",
    "label_month",
    "split",
]

SUMMARY_COLUMNS = [
    "split",
    "n_samples",
    "n_label_months",
    *[f"n_{event.value}" for event in Event],
]


def assign_temporal_split(
    samples: pd.DataFrame,
    train_end: str = "2016-12",
    validation_end: str = "2017-06",
) -> pd.DataFrame:
    """Assign labelled samples to splits using label_month boundaries."""
    required = {
        "reference_id",
        "feature_month",
        "community_id",
        "label_month",
        "label",
    }
    missing = required - set(samples.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Validate split boundaries.
    next_month(train_end)
    next_month(validation_end)

    if train_end >= validation_end:
        raise ValueError("train_end must be earlier than validation_end")

    # Validate feature_month and label_month for all rows.
    for month in samples["feature_month"]:
        next_month(month)

    for month in samples["label_month"]:
        if month != "":
            next_month(month)

    # Keep only rows with labels.
    labelled = samples.loc[
        samples["label"].notna() & (samples["label"] != "")
    ].copy()

    # The label must refer to the month immediately after feature_month.
    expected_label_months = labelled["feature_month"].map(next_month)

    if not (labelled["label_month"] == expected_label_months).all():
        raise ValueError(
            "label_month must equal next_month(feature_month)"
        )

    labelled["split"] = "test"
    labelled.loc[labelled["label_month"] <= train_end, "split"] = "train"
    labelled.loc[
        (labelled["label_month"] > train_end)
        & (labelled["label_month"] <= validation_end),
        "split",
    ] = "validation"

    counts = labelled["split"].value_counts()
    empty_splits = {"train", "validation", "test"} - set(counts.index)
    if empty_splits:
        raise ValueError(f"Empty split(s): {sorted(empty_splits)}")

    return labelled[SPLIT_COLUMNS].reset_index(drop=True)


def summarize_split(
    samples: pd.DataFrame,
    split: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize sample counts and event-class support by split."""
    required = {"reference_id", "feature_month", "community_id", "label_month", "label"}
    missing = required - set(samples.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    labelled = samples.loc[samples["label"].notna() & (samples["label"] != "")].copy()
    labelled = labelled.merge(
        split[SPLIT_COLUMNS],
        on=["reference_id", "feature_month", "community_id", "label_month"],
        how="inner",
        validate="one_to_one",
    )

    rows = []
    for split_name in ("train", "validation", "test"):
        part = labelled.loc[labelled["split"] == split_name]
        row = {
            "split": split_name,
            "n_samples": len(part),
            "n_label_months": part["label_month"].nunique(),
        }
        for event in Event:
            row[f"n_{event.value}"] = int((part["label"] == event.value).sum())
        rows.append(row)

    rows.append({
        "split": "unlabeled_dropped",
        "n_samples": int((samples["label"].isna() | (samples["label"] == "")).sum()),
        "n_label_months": 0,
        **{f"n_{event.value}": 0 for event in Event},
    })

    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)