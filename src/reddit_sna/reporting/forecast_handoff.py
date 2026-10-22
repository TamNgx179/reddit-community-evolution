"""Independent CSV consumer for the version-2 forecasting handoff."""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from reddit_sna.contracts import Event, next_month


def read_handoff(run: Path):
    """Verify hashes and joins before returning feature/label tables to partners.

    Does not import tracking, feature extraction, sklearn or model pickle files.
    Callers must retain label_reference_id when combining different label sets.
    """
    run = run.resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("schema_version") != 2:
        raise ValueError("Expected completed forecast schema version 2")
    inventory = manifest.get("artifact_hashes", {})
    required = {"features.csv", "labels.csv", "samples.csv", "predictions.csv", "metrics.json", "quality.json"}
    if not required.issubset(inventory):
        raise ValueError("Handoff missing required verified files")
    for relative, expected in inventory.items():
        path = (run / relative).resolve()
        if not path.is_relative_to(run):
            raise ValueError("Unsafe artifact path")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError("Handoff artifact hash mismatch")
    def table(name, columns):
        with (run / name).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != columns:
                raise ValueError(f"Handoff schema mismatch: {name}")
            rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("Handoff row width mismatch")
        return rows
    key_fields = ["reference_id", "feature_month", "community_id"]
    def key(row):
        if any(not row[f].strip() for f in key_fields):
            raise ValueError("Empty sample key")
        next_month(row["feature_month"])
        return tuple(row[f] for f in key_fields)
    fields = manifest["features"]
    features = table("features.csv", key_fields + ["available_through_month"] + fields)
    labels = table("labels.csv", key_fields + ["label_month", "label", "eligible", "reason", "label_reference_id"])
    samples = table("samples.csv", key_fields + ["label_month"] + fields + ["label"])
    feature_map = {key(r): r for r in features}
    label_map = {key(r): r for r in labels}
    if len(feature_map) != len(features) or len(label_map) != len(labels):
        raise ValueError("Duplicate handoff keys")
    if len({r["reference_id"] for r in features}) != 1:
        raise ValueError("Mixed or absent membership references")
    months = manifest["actual_months"]
    if (not months or months != sorted(set(months))
            or any(next_month(a) != b for a, b in zip(months, months[1:]))
            or any(row["feature_month"] not in months for row in features)):
        raise ValueError("Invalid forecast month cohort")
    last_month = months[-1]
    next_month(manifest["test_start_label_month"])
    if set(label_map) != {k for k, r in feature_map.items() if r["feature_month"] < last_month}:
        raise ValueError("Labels must cover all source communities except the last month")
    for row in features:
        if row["available_through_month"] != row["feature_month"]:
            raise ValueError("Feature availability month mismatch")
        if any(not math.isfinite(float(row[f])) for f in fields):
            raise ValueError("Nonfinite handoff features")
    for row in labels:
        if key(row) not in feature_map or row["label_month"] != next_month(row["feature_month"]):
            raise ValueError("Invalid feature-label join")
        if row["label_reference_id"] != manifest["label_reference_id"]:
            raise ValueError("Label reference mismatch")
        if row["eligible"] not in {"0", "1"} or not row["reason"]:
            raise ValueError("Invalid eligibility or missing reason")
        if row["eligible"] == "1":
            Event(row["label"])
        elif row["label"]:
            raise ValueError("Excluded row must not invent a label")
    eligible = {k for k, row in label_map.items() if row["eligible"] == "1"}
    if {key(r) for r in samples} != eligible or len(samples) != len(eligible):
        raise ValueError("Samples must equal eligible label rows")
    for row in samples:
        k = key(row)
        if (row["label"] != label_map[k]["label"] or row["label_month"] != label_map[k]["label_month"]
                or any(row[f] != feature_map[k][f] for f in fields)):
            raise ValueError("Samples differ from feature/label join")
    predictions = table("predictions.csv", key_fields + ["label_month", "model", "y_true", "y_pred"])
    sample_map = {key(r): r for r in samples}
    heldout = {k for k, r in sample_map.items() if r["label_month"] >= manifest["test_start_label_month"]}
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    if not metrics["models"] or not heldout or len(heldout) == len(samples):
        raise ValueError("Forecast requires models and nonempty train/test samples")
    if metrics["test_samples"] != len(heldout) or metrics["train_samples"] != len(samples) - len(heldout):
        raise ValueError("Metrics split counts mismatch")
    for name in metrics["models"]:
        rows = [r for r in predictions if r["model"] == name]
        if len(rows) != len(heldout) or {key(r) for r in rows} != heldout:
            raise ValueError("Prediction rows must equal held-out sample keys")
        for row in rows:
            source = sample_map[key(row)]
            if row["y_true"] != source["label"] or row["label_month"] != source["label_month"]:
                raise ValueError("Prediction target mismatch")
            Event(row["y_pred"])
        counts = Counter((r["y_true"], r["y_pred"]) for r in rows)
        result = metrics["models"][name]
        order = [e.value for e in Event]
        if result["labels"] != order or result["confusion_matrix"] != [[counts[a, b] for b in order] for a in order]:
            raise ValueError("Confusion matrix inconsistent with predictions")
        f1 = []
        for label in order:
            denominator = sum(v for (a, b), v in counts.items() if a == label) + sum(v for (a, b), v in counts.items() if b == label)
            f1.append(2 * counts[label, label] / denominator if denominator else 0.0)
        if not math.isclose(result["macro_f1"], sum(f1) / len(f1), abs_tol=1e-12):
            raise ValueError("Macro-F1 inconsistent with predictions")
        # Verify every plotted class metric, including absent-class zeroes.
        recalls = []
        for label in order:
            support = sum(v for (a, _), v in counts.items() if a == label)
            predicted = sum(v for (_, b), v in counts.items() if b == label)
            precision = counts[label, label] / predicted if predicted else 0.0
            recall = counts[label, label] / support if support else 0.0
            expected = dict(precision=precision, recall=recall,
                            **{"f1-score": 2 * precision * recall / (precision + recall) if precision + recall else 0.0},
                            support=support)
            if any(not math.isclose(result["per_class"][label][k], value, abs_tol=1e-12)
                   for k, value in expected.items()):
                raise ValueError("Per-class metrics inconsistent with predictions")
            if support:
                recalls.append(recall)
        if not recalls or not math.isclose(result["balanced_accuracy_present_classes"],
                                           sum(recalls) / len(recalls), abs_tol=1e-12):
            raise ValueError("Balanced accuracy inconsistent with predictions")
    if any(r["model"] not in metrics["models"] for r in predictions):
        raise ValueError("Unknown prediction model")
    quality = json.loads((run / "quality.json").read_text(encoding="utf-8"))
    if quality["total_source_transitions"] != len(labels) or quality["eligible_samples"] != len(samples):
        raise ValueError("Quality support mismatch")
    train_support = dict(Counter(r["label"] for r in samples if key(r) not in heldout))
    test_support = dict(Counter(r["label"] for r in samples if key(r) in heldout))
    expected_monthly = {m: dict(Counter(r["label"] or "unresolved" for r in labels if r["label_month"] == m))
                        for m in months[1:]}
    if (quality["train_support"] != train_support or quality["test_support"] != test_support
            or quality["monthly_support"] != expected_monthly
            or quality["unresolved"] != len(labels) - len(samples)
            or quality["exclusion_reasons"] != dict(Counter(r["reason"] for r in labels if r["eligible"] == "0"))
            or quality["label_reference_id"] != manifest["label_reference_id"]
            or quality["absent_test_classes"] != [e.value for e in Event if not test_support.get(e.value)]
            or not math.isclose(quality["dominant_test_fraction"], max(test_support.values()) / len(heldout), abs_tol=1e-12)):
        raise ValueError("Quality class/coverage counts inconsistent with tables")
    folds = []
    if "development_folds.json" in inventory:
        folds = json.loads((run / "development_folds.json").read_text(encoding="utf-8"))
        boundaries = sorted({r["label_month"] for r in samples if key(r) not in heldout})[2:]
        if [fold["test_start_label_month"] for fold in folds] != boundaries:
            raise ValueError("Development fold boundaries mismatch")
        for fold, boundary in zip(folds, boundaries):
            if (fold["train_samples"] != sum(r["label_month"] < boundary for r in samples)
                    or fold["test_samples"] != sum(r["label_month"] == boundary for r in samples)):
                raise ValueError("Development fold support mismatch")
            if not fold["models"] or any(not math.isfinite(model["macro_f1"]) or not 0 <= model["macro_f1"] <= 1
                                         for model in fold["models"].values()):
                raise ValueError("Invalid development fold score")
    errors = [r for r in predictions if r["y_true"] != r["y_pred"]]
    if "errors.csv" in inventory and table("errors.csv", key_fields + ["label_month", "model", "y_true", "y_pred"]) != errors:
        raise ValueError("Error examples differ from predictions")
    return {"manifest": manifest, "features": features, "labels": labels, "samples": samples,
            "metrics": metrics, "quality": quality, "predictions": predictions,
            "errors": errors, "development_folds": folds}
