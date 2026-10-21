"""B1 baselines: Majority and Persistence with Majority fallback.

Ownership: Tram (models/majority_persistence.py).
Data kind: synthetic tables -- not Reddit results.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from reddit_sna.contracts import Event


# ---------------------------------------------------------------------------
# Majority model
# ---------------------------------------------------------------------------

@dataclass
class MajorityModel:
    """Fitted majority-vote classifier. Tie-broken by Event order."""
    majority_class: Event
    class_counts: dict[str, int]

    def __repr__(self) -> str:  # pragma: no cover
        return f"MajorityModel(majority={self.majority_class.value}, counts={self.class_counts})"


def fit_majority(train: pd.DataFrame) -> MajorityModel:
    """Fit majority model on the training label column.

    Parameters
    ----------
    train:
        DataFrame with a 'label' column containing Event values (non-empty).

    Returns
    -------
    MajorityModel

    Raises
    ------
    ValueError
        If train is empty or has no labelled rows.
    """
    labelled = train[train["label"] != ""]
    if labelled.empty:
        raise ValueError("Training data is empty or has no labelled rows.")

    counts: dict[str, int] = {}
    for event in Event:
        counts[event.value] = int((labelled["label"] == event.value).sum())

    # Tie-break: earlier in list(Event) wins
    majority_val = max(list(Event), key=lambda e: counts[e.value])
    return MajorityModel(majority_class=majority_val, class_counts=counts)


def predict_majority(model: MajorityModel, samples: pd.DataFrame) -> pd.DataFrame:
    """Predict majority class for all rows.

    Returns DataFrame with columns:
        reference_id, feature_month, community_id, y_pred, used_fallback
    """
    if samples.empty:
        return pd.DataFrame(columns=[
            "reference_id", "feature_month", "community_id",
            "y_pred", "used_fallback"
        ])
    result = samples[["reference_id", "feature_month", "community_id"]].copy()
    result = result.reset_index(drop=True)
    result["y_pred"] = model.majority_class.value
    result["used_fallback"] = False
    return result


# ---------------------------------------------------------------------------
# Persistence model (uses majority model internally for fallback)
# ---------------------------------------------------------------------------

def predict_persistence(model: MajorityModel, samples: pd.DataFrame) -> pd.DataFrame:
    """Predict by repeating prev_label; fall back to Majority when prev_label is absent.

    Returns DataFrame with columns:
        reference_id, feature_month, community_id, y_pred, used_fallback
    """
    if samples.empty:
        return pd.DataFrame(columns=[
            "reference_id", "feature_month", "community_id",
            "y_pred", "used_fallback"
        ])

    valid_events = {e.value for e in Event}
    rows = []
    for _, row in samples.iterrows():
        prev = str(row.get("prev_label", "")).strip()
        if prev in valid_events:
            rows.append({
                "reference_id": row["reference_id"],
                "feature_month": row["feature_month"],
                "community_id": row["community_id"],
                "y_pred": prev,
                "used_fallback": False,
            })
        else:
            rows.append({
                "reference_id": row["reference_id"],
                "feature_month": row["feature_month"],
                "community_id": row["community_id"],
                "y_pred": model.majority_class.value,
                "used_fallback": True,
            })
    return pd.DataFrame(rows)