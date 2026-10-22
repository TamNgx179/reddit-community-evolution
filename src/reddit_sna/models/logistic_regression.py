"""B4 Logistic Regression baseline for community event prediction.

Features: size_t, size_tm1, size_tm2, age_months, growth_rate (5 numeric columns).
StandardScaler fitted on train only. Fallback to Majority when any feature is missing.
Hyperparameters fixed in B4Config; do not tune on test scores.

Ownership: Tram (models/logistic_regression.py).
Data kind: synthetic -- not Reddit results.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd

from reddit_sna.contracts import Event
from reddit_sna.models.majority_persistence import MajorityModel, fit_majority

# Features used by B4 (must match Proposal spec)
B4_FEATURES: tuple[str, ...] = (
    "size_t", "size_tm1", "size_tm2", "age_months", "growth_rate"
)


@dataclass(frozen=True)
class B4Config:
    """Fixed hyperparameters -- do not tune via test scores."""
    C: float = 1.0
    class_weight: str = "balanced"
    max_iter: int = 1000
    solver: str = "lbfgs"


@dataclass
class LogregModel:
    """Fitted B4 model with its fallback Majority model."""
    config: B4Config
    scaler: Any          # sklearn StandardScaler
    clf: Any             # sklearn LogisticRegression
    fallback: MajorityModel
    missing_train_classes: list[str]   # classes not present in train
    seed: int
    classes_in_order: list[str]        # order from Event (6 elements)


def fit_logreg(train: pd.DataFrame, seed: int, config: B4Config = B4Config()) -> LogregModel:
    """Fit B4 on train set.

    Parameters
    ----------
    train:
        DataFrame with labelled rows (label != empty) and B4_FEATURES columns.
    seed:
        Random seed passed explicitly (from config).
    config:
        Hyperparameter dataclass (fixed).

    Raises
    ------
    ValueError
        If training data has < 2 distinct classes or is empty.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    labelled = train[train["label"] != ""].copy()
    if labelled.empty:
        raise ValueError("Training data is empty.")

    fallback = fit_majority(labelled)
    unique_classes = labelled["label"].unique().tolist()
    if len(unique_classes) < 2:
        raise ValueError(
            f"LogisticRegression requires >= 2 training classes; got {unique_classes}. "
            "Recorded in missing_train_classes."
        )

    all_events = [e.value for e in Event]
    missing = [e for e in all_events if e not in unique_classes]

    # Build X_train, y_train -- rows with all B4_FEATURES present (non-NaN)
    feat_mask = labelled[list(B4_FEATURES)].notna().all(axis=1)
    usable = labelled[feat_mask]
    if usable.empty:
        raise ValueError("No training rows have all B4 features non-NaN.")
    if usable["label"].nunique() < 2:
        raise ValueError("After dropping NaN features, training set has < 2 classes.")

    X_train = usable[list(B4_FEATURES)].astype(float).values
    y_train = usable["label"].tolist()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    clf = LogisticRegression(
        C=config.C,
        class_weight=config.class_weight,
        max_iter=config.max_iter,
        solver=config.solver,
        random_state=seed,
    )
    clf.fit(X_scaled, y_train)

    return LogregModel(
        config=config,
        scaler=scaler,
        clf=clf,
        fallback=fallback,
        missing_train_classes=missing,
        seed=seed,
        classes_in_order=all_events,
    )


def predict_logreg(model: LogregModel, samples: pd.DataFrame) -> pd.DataFrame:
    """Predict on samples using fitted B4 model.

    Rows with any missing B4 feature use Majority fallback (used_fallback=True).
    Probabilities are always for all 6 Event classes; classes unseen in train get 0.

    Returns DataFrame with columns:
        reference_id, feature_month, community_id, y_pred, used_fallback,
        proba_stable, proba_grow, proba_shrink, proba_merge, proba_split, proba_dissolve
    """
    if samples.empty:
        return pd.DataFrame(columns=[
            "reference_id", "feature_month", "community_id",
            "y_pred", "used_fallback",
            "proba_stable", "proba_grow", "proba_shrink",
            "proba_merge", "proba_split", "proba_dissolve",
        ])

    all_events = model.classes_in_order  # 6 event strings in Event order
    clf_classes = list(model.clf.classes_)

    # Build a class -> probability-column index mapping
    clf_class_idx = {c: i for i, c in enumerate(clf_classes)}

    # Mask: rows with all B4 features present
    feat_present = samples[list(B4_FEATURES)].notna().all(axis=1)

    rows_list = []
    present_indices = []
    fallback_indices = []

    for i, (_, row) in enumerate(samples.iterrows()):
        if feat_present.iloc[i]:
            present_indices.append(i)
        else:
            fallback_indices.append(i)

    # Batch-predict present rows
    present_preds: dict[int, dict] = {}
    if present_indices:
        subset = samples.iloc[present_indices]
        X = subset[list(B4_FEATURES)].astype(float).values
        X_scaled = model.scaler.transform(X)
        y_preds = model.clf.predict(X_scaled)
        probas = model.clf.predict_proba(X_scaled)  # shape (n, len(clf_classes))

        for j, orig_i in enumerate(present_indices):
            row = samples.iloc[orig_i]
            proba_row: dict[str, float] = {}
            for ev in all_events:
                col_name = f"proba_{ev}"
                idx_in_clf = clf_class_idx.get(ev)
                proba_row[col_name] = float(probas[j, idx_in_clf]) if idx_in_clf is not None else 0.0
            present_preds[orig_i] = {
                "reference_id": row["reference_id"],
                "feature_month": row["feature_month"],
                "community_id": row["community_id"],
                "y_pred": str(y_preds[j]),
                "used_fallback": False,
                **proba_row,
            }

    # Fallback rows
    fallback_preds: dict[int, dict] = {}
    for orig_i in fallback_indices:
        row = samples.iloc[orig_i]
        proba_row = {f"proba_{ev}": None for ev in all_events}
        fallback_preds[orig_i] = {
            "reference_id": row["reference_id"],
            "feature_month": row["feature_month"],
            "community_id": row["community_id"],
            "y_pred": model.fallback.majority_class.value,
            "used_fallback": True,
            **proba_row,
        }

    # Reconstruct in original order
    result_rows = []
    for i in range(len(samples)):
        if i in present_preds:
            result_rows.append(present_preds[i])
        else:
            result_rows.append(fallback_preds[i])

    return pd.DataFrame(result_rows)


def save_config(config: B4Config, model: LogregModel, out_dir: Path) -> Path:
    """Save baseline_config.json to out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "model": "B4_logreg",
        "features": list(B4_FEATURES),
        "config": asdict(config),
        "seed": model.seed,
        "missing_train_classes": model.missing_train_classes,
        "scaler_mean": model.scaler.mean_.tolist(),
        "scaler_scale": model.scaler.scale_.tolist(),
        "clf_classes": list(model.clf.classes_),
    }
    path = out_dir / "baseline_config.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def save_model(model: LogregModel, out_dir: Path) -> Path:
    """Save model_B4.joblib to out_dir."""
    import joblib  # lazy import; not in pyproject yet
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "model_B4.joblib"
    joblib.dump(model, path)
    return path