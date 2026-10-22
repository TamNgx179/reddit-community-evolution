"""Evaluation helpers for event tracking and truth-to-detector mapping."""

from typing import Iterable, Mapping

from reddit_sna.contracts import Event
from reddit_sna.tracking.jaccard import jaccard

EVENT_LABELS = tuple(event.value for event in Event)
UNMATCHED = "__unmatched__"


def evaluate_events(
    truth: Iterable[Mapping[str, str]],
    prediction: Iterable[Mapping[str, str]],
) -> dict[str, object]:
    """Evaluate one event per source, retaining missing predictions."""
    truth_rows = list(truth)
    prediction_rows = list(prediction)
    truth_by_source = {row["source_community_id"]: row["event"] for row in truth_rows}
    prediction_by_source = {
        row["source_community_id"]: row["event"] for row in prediction_rows
    }
    if len(truth_by_source) != len(truth_rows):
        raise ValueError("truth contains duplicate source communities")
    if len(prediction_by_source) != len(prediction_rows):
        raise ValueError("prediction contains duplicate source communities")
    extra_prediction_sources = sorted(
        set(prediction_by_source) - set(truth_by_source)
    )
    rows = []
    for source_id in sorted(truth_by_source):
        predicted = prediction_by_source.get(source_id, UNMATCHED)
        rows.append(
            {
                "source_community_id": source_id,
                "truth_event": truth_by_source[source_id],
                "predicted_event": predicted,
                "status": "matched" if predicted != UNMATCHED else UNMATCHED,
            }
        )
    matrix = {label: {pred: 0 for pred in (*EVENT_LABELS, UNMATCHED)} for label in EVENT_LABELS}
    for row in rows:
        if row["truth_event"] not in matrix:
            raise ValueError(f"unknown truth event: {row['truth_event']}")
        if row["predicted_event"] not in matrix[row["truth_event"]]:
            raise ValueError(f"unknown predicted event: {row['predicted_event']}")
        matrix[row["truth_event"]][row["predicted_event"]] += 1
    metrics = {}
    for label in EVENT_LABELS:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        predicted_total = sum(matrix[truth_label][label] for truth_label in EVENT_LABELS)
        precision = tp / predicted_total if predicted_total else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    macro_f1 = sum(metrics[label]["f1"] for label in EVENT_LABELS) / len(EVENT_LABELS)
    return {
        "event_predictions": rows,
        "metrics": metrics,
        "macro_f1": macro_f1,
        "confusion_matrix": matrix,
        "support": len(rows),
        "matched_support": sum(row["status"] == "matched" for row in rows),
        "unmatched_truth_sources": [
            row["source_community_id"]
            for row in rows
            if row["status"] == UNMATCHED
        ],
        "extra_prediction_sources": extra_prediction_sources,
    }


def map_source_communities(
    truth: Mapping[str, Iterable[str]],
    detector: Mapping[str, Iterable[str]],
    *,
    tau: float = 0.30,
) -> dict[str, object]:
    """Greedily map source communities using deterministic Jaccard matching."""
    if not 0 <= tau <= 1:
        raise ValueError("tau must be in [0, 1]")
    candidates = [
        {
            "truth_community_id": truth_id,
            "detector_community_id": detector_id,
            "jaccard": jaccard(truth_members, detector_members),
        }
        for truth_id, truth_members in truth.items()
        for detector_id, detector_members in detector.items()
        if jaccard(truth_members, detector_members) >= tau
    ]
    candidates.sort(key=lambda row: (-row["jaccard"], row["truth_community_id"], row["detector_community_id"]))
    used_truth: set[str] = set()
    used_detector: set[str] = set()
    mapping = []
    for row in candidates:
        if row["truth_community_id"] not in used_truth and row["detector_community_id"] not in used_detector:
            mapping.append({**row, "status": "matched"})
            used_truth.add(row["truth_community_id"])
            used_detector.add(row["detector_community_id"])
    return {
        "mapping": mapping,
        "unmatched_truth": sorted(set(truth) - used_truth),
        "extra_detector": sorted(set(detector) - used_detector),
        "tau": tau,
    }


def project_detector_events(
    truth_groups: Mapping[str, Iterable[str]],
    detector_groups: Mapping[str, Iterable[str]],
    detector_events: Iterable[Mapping[str, str]],
    *,
    tau: float = 0.30,
) -> dict[str, object]:
    """Project detector event labels onto truth sources for evaluation.

    Mapping is performed only here, as an evaluator operation. It is never
    used by the tracker to influence event assignment.
    """
    result = map_source_communities(truth_groups, detector_groups, tau=tau)
    detector_rows = list(detector_events)
    detector_by_source = {
        row["source_community_id"]: row["event"] for row in detector_rows
    }
    if len(detector_by_source) != len(detector_rows):
        raise ValueError("detector events contain duplicate source communities")
    reverse_mapping = {
        row["truth_community_id"]: row["detector_community_id"]
        for row in result["mapping"]
    }
    predictions = []
    for truth_id in sorted(truth_groups):
        detector_id = reverse_mapping.get(truth_id)
        event = detector_by_source.get(detector_id) if detector_id is not None else None
        predictions.append(
            {
                "source_community_id": truth_id,
                "event": event if event is not None else UNMATCHED,
                "status": "matched" if event is not None else UNMATCHED,
                "detector_community_id": detector_id,
            }
        )
    return {
        **result,
        "event_predictions": predictions,
        "missing_detector_events": sorted(
            set(reverse_mapping.values()) - set(detector_by_source)
        ),
    }
