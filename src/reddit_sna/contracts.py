"""Versioned in-memory records shared by algorithms and pipelines.

Disk adapters should serialize these fields explicitly. Community IDs are local
to a snapshot; only tracking links express continuity across months.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from math import isfinite
from typing import Mapping

SCHEMA_VERSION = 1


class PipelineName(StrEnum):
    CORE = "core"
    DETECTION_TRACKING = "detection-tracking"
    PREDICTION = "prediction"


class Event(StrEnum):
    STABLE = "stable"
    GROW = "grow"
    SHRINK = "shrink"
    MERGE = "merge"
    SPLIT = "split"
    DISSOLVE = "dissolve"


def next_month(month: str) -> str:
    """Validate YYYY-MM and return the following calendar month."""
    if not isinstance(month, str) or len(month) != 7:
        raise ValueError("month must use YYYY-MM")
    current = date.fromisoformat(f"{month}-01")
    if current.month == 12:
        return date(current.year + 1, 1, 1).strftime("%Y-%m")
    return date(current.year, current.month + 1, 1).strftime("%Y-%m")


def _identifiers(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("identifiers must be nonempty strings")


@dataclass(frozen=True)
class SampleKey:
    reference_id: str
    feature_month: str
    community_id: str

    def __post_init__(self) -> None:
        _identifiers(self.reference_id, self.community_id)
        next_month(self.feature_month)


@dataclass(frozen=True)
class SnapshotEdge:
    month: str
    source_user_id: str
    target_user_id: str
    weight: float

    def __post_init__(self) -> None:
        next_month(self.month)
        _identifiers(self.source_user_id, self.target_user_id)
        if self.source_user_id == self.target_user_id:
            raise ValueError("snapshot edges must not contain self-loops")
        if not isfinite(self.weight) or self.weight <= 0:
            raise ValueError("edge weight must be finite and positive")


@dataclass(frozen=True)
class Membership:
    reference_id: str
    month: str
    community_id: str
    user_id: str

    def __post_init__(self) -> None:
        _identifiers(self.reference_id, self.community_id, self.user_id)
        next_month(self.month)


@dataclass(frozen=True)
class TrackingLink:
    source: SampleKey
    target: SampleKey | None

    def __post_init__(self) -> None:
        if self.target is not None:
            if self.source.reference_id != self.target.reference_id:
                raise ValueError("tracking cannot mix reference IDs")
            if next_month(self.source.feature_month) != self.target.feature_month:
                raise ValueError("tracking links must join consecutive months")


@dataclass(frozen=True)
class CommunitySample:
    key: SampleKey
    label_month: str
    label: Event
    features: Mapping[str, float | None]

    def __post_init__(self) -> None:
        if self.label_month != next_month(self.key.feature_month):
            raise ValueError("label_month must be the month after feature_month")
        if not isinstance(self.label, Event):
            raise ValueError("label must be an Event")


@dataclass(frozen=True)
class Prediction:
    key: SampleKey
    label_month: str
    model: str
    y_true: Event
    y_pred: Event

    def __post_init__(self) -> None:
        _identifiers(self.model)
        if self.label_month != next_month(self.key.feature_month):
            raise ValueError("label_month must be the month after feature_month")
        if not isinstance(self.y_true, Event) or not isinstance(self.y_pred, Event):
            raise ValueError("prediction labels must be Events")
