"""Validation checks for prediction sample tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from reddit_sna.benchmarks.community_table import SAMPLE_COLUMNS
from reddit_sna.contracts import Event, next_month


SAMPLE_KEY_COLUMNS = [
    "reference_id",
    "feature_month",
    "community_id",
]

REQUIRED_COLUMNS = list(SAMPLE_COLUMNS)

NUMERIC_COLUMNS = [
    "size_t",
    "size_tm1",
    "size_tm2",
    "age_months",
    "growth_rate",
    "retention_prev",
    "density",
    "reciprocity",
]

BOUNDED_COLUMNS = ("density", "reciprocity", "retention_prev")
NON_NEGATIVE_COLUMNS = ("size_t", "size_tm1", "size_tm2", "age_months")
ALLOWED_LABELS = {event.value for event in Event}
SPLIT_KEY_COLUMNS = [
    "reference_id",
    "feature_month",
    "community_id",
    "label_month",
]


class SampleCheckError(ValueError):
    """Raised when the sample validation report contains failures."""


def check_samples(
    samples: pd.DataFrame,
    catalog: pd.DataFrame,
    split: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return a PASS/FAIL report for sample schema, leakage and split checks."""
    results: list[dict[str, str]] = []

    def add(check: str, passed: bool, detail: str) -> None:
        results.append({
            "check": check,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        })

    missing = [column for column in REQUIRED_COLUMNS if column not in samples.columns]
    if missing:
        add("required_columns", False, f"Missing required columns: {missing}")
        return pd.DataFrame(results, columns=["check", "status", "detail"])

    # Check sample identifiers.
    invalid_keys = []
    for column in SAMPLE_KEY_COLUMNS:
        invalid = samples[column].isna() | (
            samples[column].astype("string").str.strip() == ""
        )
        if invalid.any():
            invalid_keys.append(f"{column}: {int(invalid.sum())} empty value(s)")

    add(
        "sample_keys_present",
        not invalid_keys,
        "; ".join(invalid_keys) if invalid_keys else "All sample key values are present",
    )

    duplicate_count = int(
        samples.duplicated(subset=SAMPLE_KEY_COLUMNS, keep=False).sum()
    )
    add(
        "unique_sample_keys",
        duplicate_count == 0,
        f"{duplicate_count} row(s) have duplicate sample keys",
    )

    # Check the month relationship.
    month_errors = []
    for index, row in samples.iterrows():
        feature_month = row["feature_month"]
        label_month = row["label_month"]

        if pd.isna(feature_month) or not isinstance(feature_month, str):
            month_errors.append(f"row {index}: invalid feature_month")
            continue

        try:
            expected = next_month(feature_month)
        except (ValueError, TypeError):
            month_errors.append(f"row {index}: invalid feature_month")
            continue

        if pd.isna(label_month) or not isinstance(label_month, str):
            month_errors.append(f"row {index}: invalid label_month")
        elif label_month != expected:
            month_errors.append(
                f"row {index}: expected label_month {expected}, got {label_month}"
            )

    add(
        "label_month_follows_feature_month",
        not month_errors,
        "; ".join(month_errors[:10]) if month_errors else
        "Every label_month is the month after feature_month",
    )

    # Labels must be Event values or empty. Empty labels are only allowed
    # in the final feature month.
    invalid_labels = (
        samples["label"].notna()
        & (samples["label"] != "")
        & ~samples["label"].isin(ALLOWED_LABELS)
    )
    label_errors = []
    if invalid_labels.any():
        values = sorted(samples.loc[invalid_labels, "label"].astype(str).unique())
        label_errors.append(f"invalid label value(s): {values}")

    labelled_mask = samples["label"].notna() & (samples["label"] != "")
    unlabeled_mask = ~labelled_mask
    if unlabeled_mask.any():
        final_month = samples["feature_month"].max()
        misplaced = unlabeled_mask & (samples["feature_month"] != final_month)
        if misplaced.any():
            label_errors.append(
                f"{int(misplaced.sum())} unlabeled row(s) are not in the final feature month"
            )

    add(
        "labels_valid",
        not label_errors,
        "; ".join(label_errors) if label_errors else
        "Labels are valid Event values; unlabeled rows occur only in the final feature month",
    )

    # Previous labels are optional but must be valid when present.
    invalid_prev = (
        samples["prev_label"].notna()
        & (samples["prev_label"] != "")
        & ~samples["prev_label"].isin(ALLOWED_LABELS)
    )
    prev_values = sorted(samples.loc[invalid_prev, "prev_label"].astype(str).unique())
    add(
        "previous_labels_valid",
        not invalid_prev.any(),
        f"Invalid prev_label value(s): {prev_values}" if prev_values else
        "All non-empty prev_label values are valid",
    )

    # Feature catalog checks.
    catalog_columns_ok = {"feature", "available_at"}.issubset(catalog.columns)
    if not catalog_columns_ok:
        add(
            "catalog_schema",
            False,
            "Catalog must contain 'feature' and 'available_at' columns",
        )
        catalog_features: set[str] = set()
        forbidden_features: set[str] = set()
    else:
        add("catalog_schema", True, "Catalog contains feature and available_at")
        catalog_features = set(catalog["feature"].dropna().astype(str))
        forbidden_features = set(
            catalog.loc[catalog["available_at"].astype(str) == "t+1", "feature"]
            .dropna()
            .astype(str)
        )

    allowed_non_features = set(SAMPLE_KEY_COLUMNS) | {
        "label_month",
        "label",
        "prev_label",
    }
    actual_features = set(samples.columns) - allowed_non_features
    unknown_features = sorted(actual_features - catalog_features)
    add(
        "features_in_catalog",
        not unknown_features,
        f"Feature columns missing from catalog: {unknown_features}" if unknown_features else
        "All feature columns are listed in the catalog",
    )

    unexpected_columns = sorted(
        set(samples.columns) - (catalog_features | allowed_non_features)
    )
    add(
        "no_unexpected_columns",
        not unexpected_columns,
        f"Unexpected sample columns: {unexpected_columns}" if unexpected_columns else
        "No columns outside the catalog and permitted key/label columns",
    )

    forbidden_present = sorted(set(samples.columns) & forbidden_features)
    add(
        "no_t_plus_1_features",
        not forbidden_present,
        f"Features available only at t+1 are present: {forbidden_present}"
        if forbidden_present else
        "No t+1 feature is present in the sample table",
    )

    # Numeric values may be missing, but present values must be finite.
    numeric_errors = []
    for column in NUMERIC_COLUMNS:
        numeric = pd.to_numeric(samples[column], errors="coerce")
        present = samples[column].notna()
        invalid = present & (numeric.isna() | ~np.isfinite(numeric.astype(float)))
        if invalid.any():
            numeric_errors.append(
                f"{column}: {int(invalid.sum())} invalid numeric value(s)"
            )

    add(
        "numeric_values_finite",
        not numeric_errors,
        "; ".join(numeric_errors) if numeric_errors else
        "All present numeric values are finite numbers",
    )

    range_errors = []
    for column in NON_NEGATIVE_COLUMNS:
        values = pd.to_numeric(samples[column], errors="coerce").dropna()
        if (values < 0).any():
            range_errors.append(f"{column} contains negative values")

    for column in BOUNDED_COLUMNS:
        values = pd.to_numeric(samples[column], errors="coerce").dropna()
        if ((values < 0) | (values > 1)).any():
            range_errors.append(f"{column} must be between 0 and 1")

    add(
        "numeric_ranges_valid",
        not range_errors,
        "; ".join(range_errors) if range_errors else
        "Numeric values satisfy their expected ranges",
    )

    # Optional split-aware check: train must contain at least two classes.
    if split is not None:
        missing_split_columns = set(SPLIT_KEY_COLUMNS + ["split"]) - set(split.columns)
        if missing_split_columns:
            add(
                "train_class_support",
                False,
                f"Split is missing columns: {sorted(missing_split_columns)}",
            )
        else:
            labelled = samples.loc[labelled_mask, SPLIT_KEY_COLUMNS + ["label"]]
            duplicate_sample_keys = samples.duplicated(
                subset=SPLIT_KEY_COLUMNS,
                keep=False,
            ).any()
            duplicate_split_keys = split.duplicated(
                subset=SPLIT_KEY_COLUMNS,
                keep=False,
            ).any()

            if duplicate_sample_keys or duplicate_split_keys:
                add(
                    "train_class_support",
                    False,
                    "Cannot validate train class support because sample or split keys are duplicated",
                )
            else:
                joined = labelled.merge(
                    split[SPLIT_KEY_COLUMNS + ["split"]],
                    on=SPLIT_KEY_COLUMNS,
                    how="inner",
                    validate="one_to_one",
                )
                train_labels = joined.loc[
                    joined["split"] == "train", "label"
                ]
                class_count = train_labels.nunique()
                add(
                    "train_class_support",
                    class_count >= 2,
                    f"Train contains {class_count} distinct label class(es); at least 2 required",
                )

    return pd.DataFrame(results, columns=["check", "status", "detail"])


def assert_samples_ok(report: pd.DataFrame) -> None:
    """Raise SampleCheckError if any validation check failed."""
    required_report_columns = {"check", "status", "detail"}
    missing = required_report_columns - set(report.columns)
    if missing:
        raise SampleCheckError(
            f"Validation report is missing columns: {sorted(missing)}"
        )

    failed = report.loc[report["status"] == "FAIL"]
    if not failed.empty:
        details = [
            f"{row.check}: {row.detail}"
            for row in failed.itertuples(index=False)
        ]
        raise SampleCheckError("Invalid prediction samples:\n- " + "\n- ".join(details))
