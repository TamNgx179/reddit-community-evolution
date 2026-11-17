"""Cross-cohort comparative evaluation and paired block-bootstrap for LR and HGB.

Audits sample alignment, evaluates fixed six-class Macro-F1 under absent classes,
and conducts paired block-bootstrap resampling across shared months.
"""

from collections.abc import Sequence
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reddit_sna.evaluation.diagnostics import EVENTS, KEY, prediction_units
from reddit_sna.evaluation.research import matrix_score, score

LR_DEFAULT = "hier_lr_dynamic"
HGB_DEFAULT = "hier_hgb_dynamic"


def calculate_six_class_macro_f1(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    events: Sequence[str] = EVENTS,
) -> dict[str, Any]:
    """Compute fixed six-class Macro-F1 strictly dividing by all 6 classes.

    When any class has zero support (absent from y_true), its precision,
    recall, and F1 are defined as 0.0 (zero_division=0.0).
    The resulting macro_f1_six is strictly the arithmetic mean of all 6
    classes (sum(F1) / 6.0), distinguished from macro_f1_present which
    averages only over classes with nonzero support.

    Args:
        y_true: Ground truth event labels.
        y_pred: Predicted event labels.
        events: Fixed ordered class tuple (default: 6 standard SNA events).

    Returns:
        dict containing:
            - n: total sample count
            - macro_f1_six: Macro-F1 averaged over all 6 classes
            - macro_f1_present: Macro-F1 averaged only over classes with support > 0
            - per_class: dict of precision, recall, f1, support per class
            - confusion: 6x6 confusion matrix as list of lists
    """
    if len(y_true) != len(y_pred):
        raise ValueError("Length of y_true and y_pred must match")

    event_to_idx = {e: i for i, e in enumerate(events)}
    matrix = np.zeros((len(events), len(events)), dtype=int)

    for yt, yp in zip(y_true, y_pred, strict=True):
        if yt not in event_to_idx or yp not in event_to_idx:
            raise ValueError(f"Unrecognized event label: true='{yt}', pred='{yp}'")
        matrix[event_to_idx[yt], event_to_idx[yp]] += 1

    return matrix_score(matrix)


def validate_paired_alignment(
    predictions: list[dict[str, Any]],
    proposed: str = LR_DEFAULT,
    reference: str = HGB_DEFAULT,
) -> dict[str, Any]:
    """Validate that proposed and reference models share 100% identical keys and ground truth.

    Ensures models are evaluated on identical units without key misalignment
    or ground-truth discrepancies. The full five-field KEY from diagnostics
    (reference_id, feature_month, community_id, label_month, label_reference_id)
    is used internally via prediction_units().

    Args:
        predictions: Prediction record dictionaries.
        proposed: Name of proposed model.
        reference: Name of reference comparator model.

    Returns:
        dict summarizing alignment audit:
            - status: 'PASS' or raises ValueError
            - seeds: sorted list of common evaluation seeds
            - aligned_cases_per_seed: number of matched cases per seed
            - windows: sorted list of evaluation windows
    """
    sub_preds = [r for r in predictions if r.get("model") in (proposed, reference)]
    if not sub_preds:
        raise ValueError(f"No predictions found for models '{proposed}' and '{reference}'")

    units = prediction_units(sub_preds)
    windows = sorted({u[0] for u in units})

    results_by_seed: dict[int, int] = {}
    seeds_all: set[int] = set()

    for window in windows:
        seeds = sorted({u[2] for u in units if u[0] == window})
        seeds_all.update(seeds)
        for s in seeds:
            left_key = (window, proposed, s)
            right_key = (window, reference, s)

            if left_key not in units:
                raise ValueError(f"Missing predictions for {proposed} in window={window}, seed={s}")
            if right_key not in units:
                raise ValueError(f"Missing predictions for {reference} in window={window}, seed={s}")

            left = units[left_key]
            right = units[right_key]

            if set(left.keys()) != set(right.keys()):
                missing_in_right = set(left.keys()) - set(right.keys())
                missing_in_left = set(right.keys()) - set(left.keys())
                raise ValueError(
                    f"Sample key mismatch for seed={s}, window={window}: "
                    f"left_only={len(missing_in_left)}, right_only={len(missing_in_right)}"
                )

            # Check that ground-truth labels agree across matched keys
            for k in left:
                p_true = left[k]["y_true"]
                r_true = right[k]["y_true"]
                if p_true != r_true:
                    raise ValueError(
                        f"Ground truth label disagreement on key {k}: "
                        f"{proposed}='{p_true}' vs {reference}='{r_true}'"
                    )

            results_by_seed[s] = len(left)

    return {
        "status": "PASS",
        "seeds": sorted(seeds_all),
        "aligned_cases_per_seed": results_by_seed,
        "windows": windows,
    }


def paired_block_bootstrap_comparison(
    predictions: list[dict[str, Any]],
    proposed: str = LR_DEFAULT,
    reference: str = HGB_DEFAULT,
    block_length: int = 2,
    draws: int = 2000,
    seed: int = 20261031,
    window: str = "final",
) -> dict[str, Any]:
    """Execute paired block-bootstrap resampling over common month blocks.

    In every draw, the exact same sequence of month blocks is sampled and
    applied simultaneously to both models (paired resampling).

    Args:
        predictions: Prediction record dictionaries.
        proposed: Name of proposed model.
        reference: Name of reference comparator.
        block_length: Number of contiguous months per block.
        draws: Number of bootstrap draws.
        seed: Random seed for determinism.
        window: Prediction window name.

    Returns:
        dict containing:
            - window: window name
            - proposed: proposed model name
            - reference: reference model name
            - delta: point estimate of Macro-F1 difference (proposed - reference)
            - months: count of distinct evaluation months
            - low: 2.5 percentile of bootstrap differences (95% CI lower bound)
            - high: 97.5 percentile of bootstrap differences (95% CI upper bound)
            - draws: number of draws completed
            - block_length: block length used
            - reason: descriptive status
    """
    sub_preds = [
        r for r in predictions
        if r.get("model") in (proposed, reference) and r.get("window", window) == window
    ]
    units = prediction_units(sub_preds)
    seeds = sorted({u[2] for u in units if u[0] == window})

    if not seeds:
        raise ValueError(f"No valid seeds found for window '{window}'")

    for m in (proposed, reference):
        for s in seeds:
            if (window, m, s) not in units:
                raise ValueError(f"Missing predictions for model={m}, seed={s}, window={window}")

    sample = units[(window, proposed, seeds[0])]
    # Extract distinct month timestamps (index 3 in standard KEY tuple)
    months = sorted({k[3] for k in sample})

    # Point estimate: mean macro_f1_six across seeds
    f1_prop = np.mean([
        score(list(units[(window, proposed, s)].values()))["macro_f1_six"]
        for s in seeds
    ])
    f1_ref = np.mean([
        score(list(units[(window, reference, s)].values()))["macro_f1_six"]
        for s in seeds
    ])
    delta_observed = float(f1_prop - f1_ref)

    base = {
        "window": window,
        "proposed": proposed,
        "reference": reference,
        "delta": delta_observed,
        "months": len(months),
        "draws": draws,
        "block_length": block_length,
    }

    if len(months) < 6:
        return {
            **base,
            "low": None,
            "high": None,
            "draws": 0,
            "block_length": None,
            "reason": "Fewer than six distinct months",
        }

    if block_length > len(months):
        return {
            **base,
            "low": None,
            "high": None,
            "draws": 0,
            "block_length": None,
            "reason": "block_length_exceeds_month_range",
        }

    # Precompute per-month confusion matrices for each (model, seed, month)
    matrices: dict[tuple[str, int, str], np.ndarray] = {}
    for model in (proposed, reference):
        for s in seeds:
            for month in months:
                month_rows = [
                    r for k, r in units[(window, model, s)].items()
                    if k[3] == month
                ]
                matrices[(model, s, month)] = np.asarray(
                    score(month_rows)["confusion"], dtype=int
                )

    rng = np.random.default_rng(seed)
    deltas: list[float] = []

    num_blocks = -(-len(months) // block_length)
    max_start = len(months) - block_length + 1

    for _ in range(draws):
        starts = rng.integers(0, max_start, size=num_blocks)
        # Contiguous month sequence sampled for this draw
        selected = [months[i + j] for i in starts for j in range(block_length)][:len(months)]

        # Score both models on the IDENTICAL selected month sequence
        prop_score = np.mean([
            matrix_score(sum(matrices[(proposed, s, t)] for t in selected))["macro_f1_six"]
            for s in seeds
        ])
        ref_score = np.mean([
            matrix_score(sum(matrices[(reference, s, t)] for t in selected))["macro_f1_six"]
            for s in seeds
        ])
        deltas.append(float(prop_score - ref_score))

    low = float(np.quantile(deltas, 0.025))
    high = float(np.quantile(deltas, 0.975))

    return {
        **base,
        "low": low,
        "high": high,
        "reason": "Exploratory paired month blocks",
    }
