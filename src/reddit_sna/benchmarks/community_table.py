"""Synthetic community-month table generator for the prediction pipeline.

Label generation mechanism (deterministic given seed):
  Each community has hidden state: size, density, reciprocity, fixed growth tendency mu,
  previous growth g_prev. Each month:

  1. g = mu + 0.5 * g_prev + N(0, 0.12)  (momentum -> Persistence and size history carry signal)
  2. Fixed priority order for label:
       dissolve (prob rises when small and contracting)
       -> split (rises with size)
       -> merge (rises when small, low density)
       -> remainder by g: > +theta grow, < -theta shrink, else stable
  3. With probability label_noise the label is replaced by another class (tracker noise).
  4. Size updated per event; new communities born via birth_rate (Poisson/month); dissolve stops.
  5. Features at t use only information <= t.
     growth_target (g of t->t+1), size_{t+1}, retention t->t+1 are NEVER written to any column.

Parameters are fixed in TableParams before any test evaluation.
Data kind: synthetic -- not Reddit results.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reddit_sna.contracts import Event, next_month

# ---------------------------------------------------------------------------
# Column schema - exactly 14 columns in section 3.1 order
# ---------------------------------------------------------------------------

SAMPLE_COLUMNS: tuple[str, ...] = (
    "reference_id",   # 1  key
    "feature_month",  # 2  key
    "community_id",   # 3  key (local per month, c0000...)
    "label_month",    # 4  = next_month(feature_month)
    "label",          # 5  Event value or empty (last feature month only)
    "prev_label",     # 6  Event value or empty (t-1->t, text, not numeric)
    "size_t",         # 7  Int64
    "size_tm1",       # 8  Int64, empty if no history
    "size_tm2",       # 9  Int64, empty if no history
    "age_months",     # 10 Int64
    "growth_rate",    # 11 float64, empty if missing t-1
    "retention_prev", # 12 float64, empty if no history (past t-1->t only)
    "density",        # 13 float64
    "reciprocity",    # 14 float64
)

_NUMERIC_DTYPES: dict[str, Any] = {
    "size_t": "Int64",
    "size_tm1": "Int64",
    "size_tm2": "Int64",
    "age_months": "Int64",
    "growth_rate": "float64",
    "retention_prev": "float64",
    "density": "float64",
    "reciprocity": "float64",
}

# Feature columns that enter CommunitySample.features (numeric only, NaN->None)
FEATURE_COLS: tuple[str, ...] = (
    "size_t", "size_tm1", "size_tm2", "age_months",
    "growth_rate", "retention_prev", "density", "reciprocity",
)

_DEFAULT_TRAIN_START = "2015-02"
_DEFAULT_TRAIN_END = "2016-12"


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TableParams:
    """Fixed simulation parameters. Set once; do not tune based on test scores."""
    reference_id: str = "synthetic-v1"
    first_month: str = "2015-01"
    n_months: int = 36          # 2015-01 ... 2017-12
    n_initial: int = 40
    birth_rate: float = 3.0     # Poisson per month
    growth_threshold: float = 0.15
    label_noise: float = 0.05
    min_size: int = 3


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

@dataclass
class _State:
    size: int
    density: float
    reciprocity: float
    mu: float
    g_prev: float = 0.0
    age: int = 0
    size_tm1: int | None = None
    size_tm2: int | None = None
    prev_event: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _months_seq(first: str, n: int) -> list[str]:
    ms = [first]
    for _ in range(n - 1):
        ms.append(next_month(ms[-1]))
    return ms


def _resolve_event(g: float, size: int, density: float, theta: float,
                   rng: np.random.Generator) -> Event:
    """Priority order: dissolve > split > merge > grow/shrink/stable."""
    small = max(0.0, 1.0 - size / 20.0)
    shrinking = max(0.0, -g / 0.5)
    p_dissolve = min(0.5, 0.04 * (1 + small) * (1 + shrinking))
    if rng.random() < p_dissolve:
        return Event.DISSOLVE
    p_split = min(0.4, 0.002 * size)
    if rng.random() < p_split:
        return Event.SPLIT
    low_d = max(0.0, 1.0 - density * 5)
    p_merge = min(0.35, 0.05 * (1 + small + low_d))
    if rng.random() < p_merge:
        return Event.MERGE
    if g > theta:
        return Event.GROW
    if g < -theta:
        return Event.SHRINK
    return Event.STABLE


def _apply_noise(event: Event, noise: float, rng: np.random.Generator) -> Event:
    if rng.random() < noise:
        others = [e for e in Event if e != event]
        return others[int(rng.integers(0, len(others)))]
    return event


def _update_size(st: _State, event: Event, min_size: int, rng: np.random.Generator) -> None:
    s = st.size
    if event == Event.GROW:
        s = s + max(1, int(rng.poisson(s * 0.2)))
    elif event == Event.SHRINK:
        s = max(min_size, s - max(1, int(rng.poisson(s * 0.15))))
    elif event == Event.SPLIT:
        s = max(min_size, s // 2)
    elif event == Event.MERGE:
        s = max(min_size, s - max(1, int(rng.poisson(s * 0.1))))
    st.size = s


def _retention(prev: int | None, cur: int) -> float | None:
    if prev is None or prev == 0:
        return None
    return min(prev, cur) / max(prev, cur)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_community_table(seed: int, params: TableParams = TableParams()) -> pd.DataFrame:
    """Return deterministic synthetic community-month table (14 columns).

    Raises ValueError if any Event class has < 15 samples in default train range.
    """
    rng = np.random.default_rng(seed)
    months = _months_seq(params.first_month, params.n_months)
    last_month = months[-1]

    # Initialise
    active: list[_State] = []
    for _ in range(params.n_initial):
        active.append(_State(
            size=int(rng.integers(5, 80)),
            density=float(rng.uniform(0.05, 0.8)),
            reciprocity=float(rng.uniform(0.2, 0.9)),
            mu=float(rng.normal(0.0, 0.08)),
        ))

    rows: list[dict] = []

    for month in months:
        is_last = (month == last_month)
        label_month = next_month(month)

        # Local IDs: shuffled permutation (no lineage)
        local_ids = [f"c{i:04d}" for i in range(len(active))]
        rng.shuffle(local_ids)

        surviving: list[_State] = []
        for local_cid, st in zip(local_ids, active):
            eps = float(rng.normal(0.0, 0.12))
            g = st.mu + 0.5 * st.g_prev + eps

            # Features at t use only past info
            if st.size_tm1 is not None and st.size_tm1 > 0:
                growth_rate: float | None = (st.size - st.size_tm1) / st.size_tm1
            else:
                growth_rate = None
            retention = _retention(st.size_tm1, st.size)

            if is_last:
                label_val = ""
                event = None
            else:
                raw = _resolve_event(g, st.size, st.density, params.growth_threshold, rng)
                event = _apply_noise(raw, params.label_noise, rng)
                label_val = event.value

            rows.append({
                "reference_id": params.reference_id,
                "feature_month": month,
                "community_id": local_cid,
                "label_month": label_month,
                "label": label_val,
                "prev_label": st.prev_event,
                "size_t": st.size,
                "size_tm1": st.size_tm1,
                "size_tm2": st.size_tm2,
                "age_months": st.age,
                "growth_rate": growth_rate,
                "retention_prev": retention,
                "density": st.density,
                "reciprocity": st.reciprocity,
            })

            if not is_last and event is not None:
                old_size = st.size          # size AT t before the event mutates it
                _update_size(st, event, params.min_size, rng)
                st.size_tm2 = st.size_tm1  # shift history back
                st.size_tm1 = old_size     # record size at t (NOT the post-event size)
                st.g_prev = g
                st.age += 1
                st.prev_event = event.value
                if event != Event.DISSOLVE:
                    surviving.append(st)
            else:
                surviving.append(st)

        # Births
        if not is_last:
            n_births = int(rng.poisson(params.birth_rate))
            for _ in range(n_births):
                surviving.append(_State(
                    size=int(rng.integers(params.min_size, 30)),
                    density=float(rng.uniform(0.05, 0.8)),
                    reciprocity=float(rng.uniform(0.2, 0.9)),
                    mu=float(rng.normal(0.0, 0.08)),
                ))
        active = surviving

    df = pd.DataFrame(rows, columns=list(SAMPLE_COLUMNS))
    for col, dtype in _NUMERIC_DTYPES.items():
        df[col] = df[col].astype(dtype)

    _check_train_support(df, _DEFAULT_TRAIN_START, _DEFAULT_TRAIN_END)
    return df


def _check_train_support(df: pd.DataFrame, train_start: str, train_end: str,
                         min_support: int = 15) -> None:
    mask = (
        (df["label_month"] >= train_start)
        & (df["label_month"] <= train_end)
        & (df["label"] != "")
    )
    counts = df.loc[mask, "label"]
    for event in Event:
        n = (counts == event.value).sum()
        if n < min_support:
            raise ValueError(
                f"Class '{event.value}' has {n} train samples (need >= {min_support})."
                " Adjust TableParams (not based on test score)."
            )


# ---------------------------------------------------------------------------
# Feature catalog (M2)
# ---------------------------------------------------------------------------

def feature_catalog() -> pd.DataFrame:
    """Feature catalog per section 3.1; available_at is never 't+1'."""
    rows = [
        {"feature": "prev_label",      "dtype": "str",     "source": "synthetic_generator",
         "window": "t-1", "available_at": "t", "allowed_models": "B1_persistence",
         "note": "Event t-1->t; known at t; text column, not in numeric features"},
        {"feature": "size_t",          "dtype": "Int64",   "source": "synthetic_generator",
         "window": "t",   "available_at": "t",   "allowed_models": "B4_logreg",
         "note": "Community size at t"},
        {"feature": "size_tm1",        "dtype": "Int64",   "source": "synthetic_generator",
         "window": "t-1", "available_at": "t-1", "allowed_models": "B4_logreg",
         "note": "Community size at t-1; empty if no history"},
        {"feature": "size_tm2",        "dtype": "Int64",   "source": "synthetic_generator",
         "window": "t-2", "available_at": "t-2", "allowed_models": "B4_logreg",
         "note": "Community size at t-2; empty if no history"},
        {"feature": "age_months",      "dtype": "Int64",   "source": "synthetic_generator",
         "window": "t",   "available_at": "t",   "allowed_models": "B4_logreg",
         "note": "Months the community has existed up to t"},
        {"feature": "growth_rate",     "dtype": "float64", "source": "synthetic_generator",
         "window": "t-1", "available_at": "t", "allowed_models": "B4_logreg",
         "note": "(size_t - size_tm1) / size_tm1; known at t; empty if size_tm1 missing"},
        {"feature": "retention_prev",  "dtype": "float64", "source": "synthetic_generator",
         "window": "t-1", "available_at": "t", "allowed_models": "reserved",
         "note": "Past retention t-1->t; known at t; retention t->t+1 is target-derived, forbidden"},
        {"feature": "density",         "dtype": "float64", "source": "synthetic_generator",
         "window": "t",   "available_at": "t",   "allowed_models": "reserved",
         "note": "Structural density at t; not used by B4 week-1"},
        {"feature": "reciprocity",     "dtype": "float64", "source": "synthetic_generator",
         "window": "t",   "available_at": "t",   "allowed_models": "reserved",
         "note": "Structural reciprocity at t; not used by B4 week-1"},
    ]
    return pd.DataFrame(rows, columns=[
        "feature", "dtype", "source", "window", "available_at", "allowed_models", "note"
    ])


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def write_table(table: pd.DataFrame, catalog: pd.DataFrame,
                out_dir: Path) -> dict[str, Path]:
    """Write samples.csv and feature_catalog.csv to out_dir (UTF-8, LF)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sp = out_dir / "samples.csv"
    cp = out_dir / "feature_catalog.csv"
    table.to_csv(sp, index=False, lineterminator="\n", encoding="utf-8")
    catalog.to_csv(cp, index=False, lineterminator="\n", encoding="utf-8")
    return {"samples.csv": sp, "feature_catalog.csv": cp}


def read_table(path: Path) -> pd.DataFrame:
    """Read samples.csv with explicit dtypes; community_id always str."""
    path = Path(path)
    df = pd.read_csv(
        path,
        dtype={"reference_id": str, "feature_month": str, "community_id": str,
               "label_month": str, "label": str, "prev_label": str},
        keep_default_na=True,
    )
    for col in ("size_t", "size_tm1", "size_tm2", "age_months"):
        df[col] = df[col].astype("Int64")
    for col in ("growth_rate", "retention_prev", "density", "reciprocity"):
        df[col] = df[col].astype("float64")
    df["label"] = df["label"].fillna("")
    df["prev_label"] = df["prev_label"].fillna("")
    return df


def csv_sha256(path: Path) -> str:
    """Return hex SHA-256 of a file (for determinism checks)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()