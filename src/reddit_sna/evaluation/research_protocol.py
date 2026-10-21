"""Strict, runtime-enforced development protocol for the midterm experiment.

This protocol is frozen before fitting, but uses already inspected pilot data.
It is not a preregistration made before exposure to that data.
"""

import json
from pathlib import Path
import tomllib

from reddit_sna.contracts import next_month
from reddit_sna.features.community import FEATURES
from reddit_sna.features.history import HISTORY_FEATURES
from reddit_sna.features.context import CONTEXT_FEATURES
from reddit_sna.features.lagged import LAG_FEATURES, DYNAMICS_FEATURES

HGB = dict(learning_rate=0.05, max_iter=100, max_depth=3, max_leaf_nodes=7,
           min_samples_leaf=20, l2_regularization=1.0, early_stopping=False,
           class_weight="balanced", categorical_features=None)
RF = dict(n_estimators=100, max_depth=6, min_samples_leaf=5,
          class_weight="balanced", n_jobs=1)
LR = dict(C=1.0, max_iter=2000)
BASE = FEATURES + HISTORY_FEATURES + LAG_FEATURES
FULL = BASE + CONTEXT_FEATURES
VARIANTS = {
    "B1_majority": (), "B1_persistence": (), "B4_logreg": FEATURES + HISTORY_FEATURES,
    "B2_random_forest": BASE, "B5_matched_boosting": BASE, "HeTCo_v0": FULL,
    "A1_no_context": BASE,
    "A4_no_dynamics": tuple(f for f in FULL if f not in DYNAMICS_FEATURES),
    "A6_no_lag": tuple(f for f in FULL if f not in LAG_FEATURES),
}


def load_protocol(path):
    """Reject unknown fields, unbounded schedules and undeclared model settings."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    expected = {"schema_version", "protocol_id", "exposure", "test_start", "seeds",
                "rolling_months", "bootstrap", "hgb", "rf", "lr"}
    if set(data) != expected:
        raise ValueError("Research protocol fields differ from the supported schema")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported research protocol schema")
    if data["protocol_id"] != "midterm-context-history-v1" or data["exposure"] != "inspected_development_data":
        raise ValueError("Research protocol must declare inspected development data")
    next_month(data["test_start"])
    seeds, months = data["seeds"], data["rolling_months"]
    if (not isinstance(seeds, list) or seeds != [42, 43, 44]
            or any(type(x) is not int for x in seeds)):
        raise ValueError("Research seeds must be the predeclared 42/43/44")
    if (not isinstance(months, list) or len(months) != 6 or months != sorted(set(months))
            or any(next_month(a) != b for a, b in zip(months, months[1:]))):
        raise ValueError("Rolling diagnostics require six consecutive label months")
    for month in months:
        next_month(month)
    if not months[0] < data["test_start"] <= months[-1]:
        raise ValueError("Main holdout must start inside the rolling interval")
    expected_bootstrap = dict(block_length=2, draws=1000, seed=2026, minimum_months=6)
    # JSON comparison distinguishes bool from int. None is encoded as a fixed
    # implementation choice because TOML does not represent null.
    for name, actual, wanted in (("bootstrap", data["bootstrap"], expected_bootstrap),
                                  ("hgb", data["hgb"], {k: v for k, v in HGB.items() if k != "categorical_features"}),
                                  ("rf", data["rf"], RF), ("lr", data["lr"], LR)):
        if json.dumps(actual, sort_keys=True) != json.dumps(wanted, sort_keys=True):
            raise ValueError(f"Unsupported {name} settings; do not retune after evaluation")
    return data


def resolved_protocol(data):
    """Record feature order, exact parameters, estimands and human limitations."""
    return {**data, "hgb": HGB, "variants": {k: list(v) for k, v in VARIANTS.items()},
            "tuning_budget": "one fixed configuration per variant; no parameter search",
            "reference_policy": "identical eligible sample/label/reference keys for every variant",
            "method_scope": "project-defined preliminary context/history forecaster; not full final HeTCo",
            "unseen": False, "human_annotation": "pending", "novelty": "unverified",
            "primary_metric": "fixed-six-class macro-F1; zero_division=0",
            "seed_aggregation": "mean of seed-specific scores/deltas, not independent time samples",
            "uncertainty_scope": "exploratory rolling-month block bootstrap; no confirmatory claim",
            "memory_policy": "native peak unmeasured; report null with reason"}
