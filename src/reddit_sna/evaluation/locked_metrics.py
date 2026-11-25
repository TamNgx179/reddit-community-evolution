"""Locked six-class metrics and paired contiguous-month bootstrap evaluation.

The evaluator is deliberately prediction-only: it never fits or selects models.
All six event classes are retained in every metric and confusion matrix.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
import math

import numpy as np
import pandas as pd



LABELS = ("stable", "grow", "shrink", "merge", "split", "dissolve")
KEY_COLUMNS = ("reference_id", "feature_month", "community_id", "label_month", "label_reference_id")
REQUIRED_COLUMNS = (*KEY_COLUMNS, "cohort", "model", "seed", "y_true", "y_pred")
BOOTSTRAP_DRAWS = 2_000
BLOCK_LENGTH_MONTHS = 3
BOOTSTRAP_SEED = 2026



def _f1_from_confusion(matrix: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Return six-class Macro-F1, precision, recall and F1 (zero for empty classes)."""
    matrix = np.asarray(matrix, dtype=np.int64)
    if matrix.shape != (6, 6):
        raise ValueError("confusion matrix must be 6x6")
    support = matrix.sum(axis=1)
    predicted = matrix.sum(axis=0)
    tp = np.diag(matrix)
    precision = np.divide(tp, predicted, out=np.zeros(6, dtype=float), where=predicted != 0)
    recall = np.divide(tp, support, out=np.zeros(6, dtype=float), where=support != 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros(6, dtype=float), where=(precision + recall) != 0)
    return float(f1.mean()), precision, recall, f1


def _matrix(rows: pd.DataFrame) -> np.ndarray:
    indexes = {label: i for i, label in enumerate(LABELS)}
    cm = np.zeros((6, 6), dtype=np.int64)
    for truth, pred in zip(rows.y_true, rows.y_pred):
        cm[indexes[truth], indexes[pred]] += 1
    return cm


def validate_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(predictions.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    data = predictions.loc[:, REQUIRED_COLUMNS].copy()
    if data.empty:
        raise ValueError("predictions file is empty")
    if data.isna().any().any() or data.astype(str).apply(lambda c: c.str.strip().eq("")).any().any():
        raise ValueError("required fields cannot be blank or null")
    invalid = (set(data.y_true.astype(str)) | set(data.y_pred.astype(str))) - set(LABELS)
    if invalid:
        raise ValueError(f"unknown event label(s): {sorted(invalid)}")
    data["seed"] = pd.to_numeric(data.seed, errors="raise").astype(int)
    # Strict month format and chronological order are needed for block sampling.
    for col in ("feature_month", "label_month"):
        parsed = pd.to_datetime(data[col] + "-01", format="%Y-%m-%d", errors="coerce")
        if parsed.isna().any() or (parsed.dt.strftime("%Y-%m") != data[col]).any():
            raise ValueError(f"invalid YYYY-MM values in {col}")
    key = ["cohort", *KEY_COLUMNS]
    if data.duplicated([*key, "model", "seed"]).any():
        raise ValueError("duplicate cohort/sample/model/seed prediction rows")
    if (pd.to_datetime(data.label_month + "-01") !=
            pd.to_datetime(data.feature_month + "-01") + pd.offsets.MonthBegin(1)).any():
        raise ValueError("label_month must be the month immediately after feature_month")
    # Each cohort/model/seed must predict exactly the same key set and truths.
    reference_keys = None
    reference_truth = None
    for cohort, cohort_data in data.groupby("cohort", sort=True):
        model_seed_sets = {model: set(group.seed.astype(int)) for model, group in cohort_data.groupby("model")}
        seed_sets = list(model_seed_sets.values())
        if seed_sets and any(seed_set != seed_sets[0] for seed_set in seed_sets[1:]):
            raise ValueError(f"models do not share the same seed set in cohort {cohort}")
        sample_key = [*KEY_COLUMNS]
        keys_truth = cohort_data[sample_key + ["y_true"]].drop_duplicates().sort_values(sample_key)
        if keys_truth.duplicated(sample_key).any():
            raise ValueError(f"inconsistent y_true across models/seeds in cohort {cohort}")
        expected = tuple(map(tuple, keys_truth[sample_key].to_numpy().tolist()))
        truths = tuple(keys_truth.y_true.tolist())
        for (model, seed), group in cohort_data.groupby(["model", "seed"], sort=True):
            actual = tuple(map(tuple, group[sample_key].sort_values(sample_key).to_numpy().tolist()))
            sorted_truth = group.sort_values(sample_key).y_true.tolist()
            if actual != expected or sorted_truth != list(truths):
                raise ValueError(f"incomplete or misaligned predictions for {cohort}/{model}/seed={seed}")
    return data



def evaluate_locked(predictions: pd.DataFrame, *, draws: int = BOOTSTRAP_DRAWS,
                  block_length: int = BLOCK_LENGTH_MONTHS, seed: int = BOOTSTRAP_SEED) -> dict[str, pd.DataFrame]:
    """Generate class/month metrics, confusions and pairwise bootstrap CIs per cohort."""
    if draws < 1 or block_length < 1:
        raise ValueError("draws and block_length must be positive")
    data = validate_predictions(predictions)
    monthly_rows, class_rows, confusion_rows, overall_rows, overall_confusion_rows = [], [], [], [], []

    # Keep seed-level results; model summaries average seed scores, not pooled rows.
    monthly_cm: dict[tuple, np.ndarray] = {}
    for (cohort, model, model_seed, month), group in data.groupby(
            ["cohort", "model", "seed", "label_month"], sort=True):
        cm = _matrix(group)
        score, precision, recall, f1 = _f1_from_confusion(cm)
        monthly_cm[(cohort, model, int(model_seed), month)] = cm
        monthly_rows.append({"cohort": cohort, "model": model, "seed": int(model_seed),
                            "label_month": month, "n": int(cm.sum()), "macro_f1_six": score})
        for i, label in enumerate(LABELS):
            class_rows.append({"cohort": cohort, "model": model, "seed": int(model_seed),
                              "label_month": month, "label": label, "precision": precision[i],
                              "recall": recall[i], "f1": f1[i], "support": int(cm[i].sum())})
        for i, truth in enumerate(LABELS):
            for j, pred in enumerate(LABELS):
                confusion_rows.append({"cohort": cohort, "model": model, "seed": int(model_seed),
                                    "label_month": month, "y_true": truth, "y_pred": pred,
                                    "count": int(cm[i, j])})

    for (cohort, model, model_seed), group in data.groupby(["cohort", "model", "seed"], sort=True):
        cm = _matrix(group)
        score, precision, recall, f1 = _f1_from_confusion(cm)
        overall_rows.append({"cohort": cohort, "model": model, "seed": int(model_seed),
                            "n": int(cm.sum()), "macro_f1_six": score})
        for i, truth in enumerate(LABELS):
            for j, pred in enumerate(LABELS):
                overall_confusion_rows.append({"cohort": cohort, "model": model, "seed": int(model_seed),
                                               "y_true": truth, "y_pred": pred, "count": int(cm[i, j])})

    monthly_df = pd.DataFrame(monthly_rows)
    cohort_months = {c: sorted(g.label_month.unique()) for c, g in data.groupby("cohort", sort=True)}
    cohorts = sorted(data.cohort.unique())
    # RNG is reset per cohort: same draw schedule across all models/pairs in cohort.
    pair_rows = []
    for cohort in cohorts:
        cohort_data = data[data.cohort == cohort]
        model_names = sorted(cohort_data.model.unique())
        seeds = sorted(cohort_data.seed.unique())
        observed_months = cohort_months[cohort]
        months = pd.date_range(observed_months[0] + "-01", observed_months[-1] + "-01", freq="MS").strftime("%Y-%m").tolist()
        rng = np.random.default_rng(seed)
        eligible_pairs = list(combinations(model_names, 2))
        if len(months) < block_length:
            for left, right in eligible_pairs:
                pair_rows.append({"cohort": cohort, "model_a": left, "model_b": right,
                                 "delta_a_minus_b": None, "ci_low": None, "ci_high": None,
                                 "draws": draws, "block_length_months": block_length,
                                 "bootstrap_seed": seed, "status": "unavailable_insufficient_months",
                                 "n_months": len(months)})
            continue
        boot_deltas = {(a, b): [] for a, b in eligible_pairs}
        monthly_matrices = {}
        for model in model_names:
            for model_seed in seeds:
                for month in months:
                    key = (cohort, model, model_seed, month)
                    monthly_matrices[(model, model_seed, month)] = monthly_cm.get(key, np.zeros((6, 6), dtype=np.int64))
        for _ in range(draws):
            n_blocks = math.ceil(len(months) / block_length)
            starts = rng.integers(0, len(months) - block_length + 1, size=n_blocks)
            selected_months = [months[start + offset] for start in starts
                              for offset in range(block_length)][:len(months)]
            scores = {}
            for model in model_names:
                seed_scores = []
                for model_seed in seeds:
                    summed = np.zeros((6, 6), dtype=np.int64)
                    for month in selected_months:
                        summed += monthly_matrices[(model, model_seed, month)]
                    seed_scores.append(_f1_from_confusion(summed)[0])
                scores[model] = float(np.mean(seed_scores))
            for a, b in eligible_pairs:
                boot_deltas[(a, b)].append(scores[a] - scores[b])
        # The observed contrast uses all months and the same six-class scoring rule.
        observed = {model: float(np.mean([r["macro_f1_six"] for r in overall_rows
                                        if r["cohort"] == cohort and r["model"] == model]))
                   for model in model_names}
        for a, b in eligible_pairs:
            values = np.asarray(boot_deltas[(a, b)], dtype=float)
            pair_rows.append({"cohort": cohort, "model_a": a, "model_b": b,
                             "delta_a_minus_b": observed[a] - observed[b],
                             "ci_low": float(np.quantile(values, 0.025)),
                             "ci_high": float(np.quantile(values, 0.975)),
                             "draws": draws, "block_length_months": block_length,
                             "bootstrap_seed": seed, "status": "percentile_paired_block_bootstrap",
                             "n_months": len(months)})
    return {
        "overall": pd.DataFrame(overall_rows),
        "monthly": monthly_df,
        "per_class_month": pd.DataFrame(class_rows),
        "confusion_month": pd.DataFrame(confusion_rows),
        "confusion_overall": pd.DataFrame(overall_confusion_rows),
        "paired_bootstrap": pd.DataFrame(pair_rows),
    }


def write_evaluation(predictions_csv: str | Path, output_dir: str | Path, **kwargs) -> dict[str, pd.DataFrame]:
    """Run from CSV and write tables into a new output directory (never overwrite)."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    raw = pd.read_csv(predictions_csv)
    results = evaluate_locked(raw, **kwargs)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, table in results.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
    return results
