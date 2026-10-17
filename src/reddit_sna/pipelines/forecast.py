"""Read verified preparation artifacts and run a temporal fallback baseline."""

import csv
import json
import math
import hashlib
from importlib.metadata import version
from pathlib import Path

from reddit_sna.contracts import Event, SampleKey, SnapshotEdge, next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.features.community import FEATURES, snapshot_features
from reddit_sna.features.history import HISTORY_FEATURES, history_features
from reddit_sna.reporting.handoff import inspect_handoff
from reddit_sna.tracking.jaccard import transitions


def _rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(samples, test_start, seed=42, *, model_store=None, feature_names=FEATURES):
    """Fit on label_month < test_start only; test on later label months.

    Single-class training uses Majority. Metrics always include all six events.
    """
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import recall_score, classification_report, confusion_matrix, f1_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    next_month(test_start)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    keys, references = set(), set()
    for row in samples:
        key = SampleKey(row["reference_id"], row["feature_month"], row["community_id"])
        if key in keys:
            raise ValueError("Duplicate sample key")
        keys.add(key)
        references.add(key.reference_id)
        if row["label_month"] != next_month(key.feature_month):
            raise ValueError("Sample label month must follow feature month")
        Event(row["label"])
        if any(type(row[f]) not in (int, float) or not math.isfinite(row[f]) for f in feature_names):
            raise ValueError("Features must be finite numeric values")
    if len(references) > 1:
        raise ValueError("Samples cannot mix reference IDs")
    train = [r for r in samples if r["label_month"] < test_start]
    test = [r for r in samples if r["label_month"] >= test_start]
    if not train or not test:
        raise ValueError("Temporal split requires nonempty train and test samples")
    xtrain = [[r[f] for f in feature_names] for r in train]
    xtest = [[r[f] for f in feature_names] for r in test]
    ytrain = [r["label"] for r in train]
    truth = [r["label"] for r in test]
    labels = [e.value for e in Event]
    models = {"majority": DummyClassifier(strategy="most_frequent")}
    if len(set(ytrain)) > 1:
        models["logistic_regression"] = make_pipeline(
            StandardScaler(), LogisticRegression(random_state=seed, max_iter=2000))
    else:
        models["logistic_regression_fallback_majority"] = DummyClassifier(strategy="most_frequent")
    predictions, metrics = [], {}
    for name, model in models.items():
        model.fit(xtrain, ytrain)
        if model_store is not None:
            model_store[name] = model
        predicted = model.predict(xtest)
        metrics[name] = {"macro_f1": f1_score(truth, predicted, labels=labels, average="macro", zero_division=0),
                         "balanced_accuracy_present_classes": recall_score(truth, predicted, labels=sorted(set(truth)), average="macro", zero_division=0),
                         "labels": labels, "confusion_matrix": confusion_matrix(truth, predicted, labels=labels).tolist(),
                         "per_class": classification_report(truth, predicted, labels=labels, output_dict=True, zero_division=0)}
        predictions.extend({**{k: r[k] for k in ("reference_id", "feature_month", "community_id", "label_month")},
                            "model": name, "y_true": r["label"], "y_pred": str(pred)}
                           for r, pred in zip(test, predicted))
    return predictions, {"train_samples": len(train), "test_samples": len(test),
                         "test_start_label_month": test_start, "models": metrics}


def run_forecast(graph_run: Path, detection_run: Path, artifact_root: Path,
                 output: Path, test_start: str, threshold=0.25, seed=42, *,
                 tracker="jaccard", alpha=0.5, beta=0.5, dissolve=0.1, history=False):
    """Never overwrite output; input integrity is checked before and after reading."""
    if not 0 < threshold <= 1:
        raise ValueError("Jaccard threshold must be in (0, 1]")
    if tracker not in {"jaccard", "ged"}:
        raise ValueError("tracker must be jaccard or ged")
    if not all(math.isfinite(v) for v in (alpha, beta, dissolve)) or not 0 < dissolve <= min(alpha, beta) <= max(alpha, beta) <= 1:
        raise ValueError("Require 0 < dissolve <= alpha,beta <= 1")
    output = output.resolve()
    if not output.is_relative_to(artifact_root.resolve()):
        raise ValueError("Forecast output must stay inside artifacts")
    if output.exists():
        raise FileExistsError("Forecast output already exists")
    source_root = Path(__file__).parents[1]
    code_hashes = {str(p.relative_to(source_root)): digest_file(p) for p in source_root.rglob("*.py")}
    acceptance = inspect_handoff(graph_run, detection_run, artifact_root)
    source_hashes = {str(p.resolve()): digest_file(p / "manifest.json") for p in (graph_run, detection_run)}
    months = [m["month"] for m in acceptance["months"]]
    if any(next_month(a) != b for a, b in zip(months, months[1:])):
        raise ValueError("Forecast requires consecutive months")
    info = json.loads((detection_run / "detection.json").read_text(encoding="utf-8"))
    groups, features, weights = {}, {}, {}
    for month in months:
        groups[month] = {}
        for row in _rows(detection_run / "memberships" / month / f"membership-seed{info['canonical_seed']}.csv"):
            groups[month].setdefault(row["community_id"], set()).add(row["user_id"])
        edges = [SnapshotEdge(r["month"], r["source_user_id"], r["target_user_id"], float(r["weight"]))
                 for r in _rows(graph_run / "snapshots" / month / "R.csv")]
        features[month] = snapshot_features(groups[month], edges)
        if tracker == "ged":
            from reddit_sna.tracking.ged import importance
            weights[month] = importance(groups[month], edges)
    tracker_config = ({"method": "ged-strength-topology-v1", "alpha": alpha, "beta": beta,
                       "dissolve": dissolve, "numeric_tolerance": 1e-12,
                       "importance": "internal_weighted_degree_zero_fallback_unit"}
                      if tracker == "ged" else {"method": "jaccard-fallback-v1", "threshold": threshold})
    label_reference = hashlib.sha256(json.dumps({"membership_reference": acceptance["canonical_reference"],
                                    **tracker_config}, sort_keys=True).encode()).hexdigest()
    feature_names = FEATURES + HISTORY_FEATURES if history else FEATURES
    samples, tracking, label_rows, pair_rows, feature_rows = [], [], [], [], []
    previous, previous_links, previous_age = None, {}, {}
    transition_data = {}
    for month, following in zip(months, months[1:]):
        if tracker == "ged":
            from reddit_sna.tracking.ged import transitions as ged_transitions
            links, events, reasons, pairs = ged_transitions(groups[month], groups[following],
                weights[month], weights[following], alpha, beta, dissolve)
            pair_rows.extend({"feature_month": month, "label_month": following, **p} for p in pairs)
        else:
            links, events = transitions(groups[month], groups[following], threshold)
            reasons = {cid: "jaccard_topology_rule" for cid in events}
        transition_data[month] = (links, events, reasons)
    # History is computed forward, before reading any outgoing label into features.
    for month in months:
        history_rows = history_features(groups[month], previous, previous_links, previous_age)
        for cid in groups[month]:
            if history:
                features[month][cid].update(history_rows[cid])
            feature_rows.append(dict(reference_id=acceptance["canonical_reference"], feature_month=month,
                                     community_id=cid, available_through_month=month, **features[month][cid]))
        previous_age = {cid: row["community_age"] for cid, row in history_rows.items()}
        previous, previous_links = groups[month], transition_data.get(month, ({},))[0]
    for month, following in zip(months, months[1:]):
        links, events, reasons = transition_data[month]
        for cid, event in events.items():
            key = dict(reference_id=acceptance["canonical_reference"], feature_month=month,
                       community_id=cid, label_month=following)
            label_rows.append({**key, "label": event.value if event else "", "eligible": int(event is not None),
                               "reason": reasons[cid], "label_reference_id": label_reference})
            if event is not None:
                samples.append({**key, **features[month][cid], "label": event.value})
            for target, score in links[cid] or [("", 0.0)]:
                tracking.append({**key, "target_community_id": target, "match_score": score,
                                 "event": event.value if event else "", "reason": reasons[cid]})
    models = {}
    predictions, metrics = evaluate(samples, test_start, seed, model_store=models, feature_names=feature_names)
    development = [r for r in samples if r["label_month"] < test_start]
    dev_months = sorted({r["label_month"] for r in development})
    rolling = []
    for boundary in dev_months[2:]:
        prefix = [r for r in development if r["label_month"] <= boundary]
        _, fold = evaluate(prefix, boundary, seed, feature_names=feature_names)
        rolling.append(fold)
    from collections import Counter
    quality = {"total_source_transitions": len(label_rows), "eligible_samples": len(samples),
               "unresolved": len(label_rows) - len(samples), "label_reference_id": label_reference,
               "exclusion_reasons": dict(Counter(r["reason"] for r in label_rows if not r["eligible"])),
               "monthly_support": {m: dict(Counter(r["label"] or "unresolved" for r in label_rows if r["label_month"] == m))
                                   for m in months[1:]},
               "train_support": dict(Counter(r["label"] for r in development)),
               "test_support": dict(Counter(r["label"] for r in samples if r["label_month"] >= test_start)),
               "label_status": "pseudo_labels_not_social_ground_truth"}
    quality["feature_months"] = {m: {"communities": len(groups[m]),
        "history_missing": sum(r.get("history_missing", 0) for r in features[m].values()) if history else None}
        for m in months}
    quality["absent_test_classes"] = [e.value for e in Event if not quality["test_support"].get(e.value)]
    quality["dominant_test_fraction"] = max(quality["test_support"].values()) / metrics["test_samples"]
    split_rows = [{**{k: r[k] for k in ("reference_id", "feature_month", "community_id", "label_month")},
                   "split": "train" if r["label_month"] < test_start else "test"} for r in samples]
    inspect_handoff(graph_run, detection_run, artifact_root)
    if any(digest_file(Path(p) / "manifest.json") != h for p, h in source_hashes.items()):
        raise ValueError("Source manifest changed during forecasting")
    if code_hashes != {str(p.relative_to(source_root)): digest_file(p) for p in source_root.rglob("*.py")}:
        raise ValueError("Forecast source code changed during execution")
    output.mkdir(parents=True, exist_ok=False)
    try:
        import joblib
        for name, model in models.items():
            joblib.dump(model, output / f"{name}.joblib")
        key_fields = ["reference_id", "feature_month", "community_id", "label_month"]
        _write(output / "samples.csv", samples, key_fields + list(feature_names) + ["label"])
        _write(output / "features.csv", feature_rows,
               ["reference_id", "feature_month", "community_id", "available_through_month"] + list(feature_names))
        _write(output / "labels.csv", label_rows, key_fields + ["label", "eligible", "reason", "label_reference_id"])
        _write(output / "tracking.csv", tracking, key_fields + ["target_community_id", "match_score", "event", "reason"])
        if tracker == "ged":
            _write(output / "inclusion_pairs.csv", pair_rows,
                   ["feature_month", "label_month", "source_community_id", "target_community_id", "shared_members",
                    "inclusion_forward", "inclusion_backward", "accepted"])
        _write(output / "predictions.csv", predictions, key_fields + ["model", "y_true", "y_pred"])
        _write(output / "errors.csv", [r for r in predictions if r["y_true"] != r["y_pred"]],
               key_fields + ["model", "y_true", "y_pred"])
        _write(output / "splits.csv", split_rows, key_fields + ["split"])
        (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        (output / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
        (output / "development_folds.json").write_text(json.dumps(rolling, indent=2) + "\n", encoding="utf-8")
        manifest = dict(status="complete", schema_version=2, tracker=tracker_config["method"], tracker_config=tracker_config,
                        actual_months=months,
                        threshold=threshold, label_reference_id=label_reference,
                        seed=seed, source_manifests=source_hashes, test_start_label_month=test_start,
                        features=list(feature_names), history=history,
                        dependencies={name: version(name) for name in ("scikit-learn", "numpy", "scipy", "joblib")},
                        source_hashes=code_hashes,
                        unimplemented=["original_GED_social_position_and_pair_event_rules", "HeTCo"],
                        label_truth="tracker-derived pseudo-labels, not social ground truth",
                        model_persistence="joblib; load only trusted locally generated models",
                        artifact_hashes={p.name: digest_file(p) for p in output.iterdir() if p.is_file()})
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        from reddit_sna.reporting.forecast_handoff import read_handoff
        read_handoff(output)  # Read back the actual CSV joins before claiming success.
    except BaseException as exc:
        failure = {"status": "failed", "failure_type": type(exc).__name__,
                   "source_manifests": source_hashes,
                   "artifact_hashes": {p.name: digest_file(p) for p in output.iterdir()
                                       if p.is_file() and p.name != "manifest.json"}}
        (output / "manifest.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        raise
    return output
