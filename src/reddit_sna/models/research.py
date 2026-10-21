"""Matched fixed-budget forecasters for the midterm development experiment."""

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from reddit_sna.evaluation.research_protocol import HGB, RF, LR, VARIANTS


def fit_variant(name, train, seed):
    """Fit only explicit training rows; all variants preserve sample availability.

    Single-class data use a named Majority fallback. HistGradientBoosting has
    no internal random validation split, and B5/A1/proposed share all settings.
    """
    if name not in VARIANTS or not train:
        raise ValueError("Unknown research variant or empty training window")
    fields = VARIANTS[name]
    truth = [r["label"] for r in train]
    fallback = name.startswith("B1_") or len(set(truth)) < 2
    if fallback:
        model = DummyClassifier(strategy="most_frequent")
    elif name == "B4_logreg":
        model = make_pipeline(StandardScaler(), LogisticRegression(random_state=seed, **LR))
    elif name == "B2_random_forest":
        model = RandomForestClassifier(random_state=seed, **RF)
    else:
        model = HistGradientBoostingClassifier(random_state=seed, **HGB)
    matrix = [[float(r[f]) for f in fields] for r in train] if fields else [[0.0] for _ in train]
    if not np.isfinite(matrix).all():
        raise ValueError("Research features must be finite")
    model.fit(matrix, truth)
    return dict(model=model, fields=fields, name=name,
                single_class_fallback=len(set(truth)) < 2,
                majority=model.classes_[int(np.argmax(model.class_prior_))] if fallback else None)


def predict_variant(fitted, rows):
    """Predict every row and separately flag persistence/single-class fallback."""
    fields = fitted["fields"]
    matrix = [[float(r[f]) for f in fields] for r in rows] if fields else [[0.0] for _ in rows]
    if not np.isfinite(matrix).all():
        raise ValueError("Research features must be finite")
    predicted = fitted["model"].predict(matrix)
    fallback = [int(fitted["single_class_fallback"]) for _ in rows]
    if fitted["name"] == "B1_persistence":
        predicted = [r["past_event"] or p for r, p in zip(rows, predicted)]
        fallback = [int(not r["past_event"]) for r in rows]
    return list(predicted), fallback
