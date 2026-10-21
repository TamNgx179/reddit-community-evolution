"""Independent event scoring, matched comparisons and time-block uncertainty.

No feature extractor, fitted model or producer is imported here. Six classes
remain in every confusion matrix, including zero-support bootstrap resamples.
"""

from collections import defaultdict
import math
import numpy as np

from reddit_sna.contracts import Event, next_month
from reddit_sna.evaluation.research_protocol import VARIANTS

EVENTS = tuple(e.value for e in Event)
KEY = ("reference_id", "feature_month", "community_id", "label_month", "label_reference_id")


def matrix_score(matrix):
    """Compute both macro conventions and supported-class balanced accuracy."""
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (6, 6) or not np.isfinite(matrix).all() or (matrix < 0).any():
        raise ValueError("Confusion matrix must contain finite nonnegative six-class counts")
    support, predicted = matrix.sum(axis=1), matrix.sum(axis=0)
    precision = np.divide(np.diag(matrix), predicted, out=np.zeros(6), where=predicted != 0)
    recall = np.divide(np.diag(matrix), support, out=np.zeros(6), where=support != 0)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros(6), where=(precision + recall) != 0)
    present = support > 0
    return dict(n=int(support.sum()), macro_f1_six=float(f1.mean()),
                macro_f1_present=float(f1[present].mean()) if present.any() else None,
                balanced_accuracy=float(recall[present].mean()) if present.any() else None,
                per_class={e: dict(precision=float(precision[i]), recall=float(recall[i]),
                                   f1=float(f1[i]), support=int(support[i])) for i, e in enumerate(EVENTS)},
                confusion=matrix.astype(int).tolist())


def score(rows):
    matrix = np.zeros((6, 6), dtype=int)
    for row in rows:
        if row["y_true"] not in EVENTS or row["y_pred"] not in EVENTS:
            raise ValueError("Unknown research event label")
        matrix[EVENTS.index(row["y_true"]), EVENTS.index(row["y_pred"])] += 1
    result = matrix_score(matrix)
    result["fallback"] = sum(int(r["fallback"]) for r in rows)
    return result


def analyze_predictions(rows, protocol):
    """Refuse missing/duplicate predictions before computing scores or intervals."""
    if not rows:
        raise ValueError("Research predictions are empty")
    groups, monthly = defaultdict(list), defaultdict(list)
    seen, samples = set(), {}
    for r in rows:
        if (r["window"] not in {"main", "rolling"} or r["model"] not in VARIANTS
                or type(r["seed"]) is not int or r["seed"] not in protocol["seeds"]
                or str(r["fallback"]) not in {"0", "1"}):
            raise ValueError("Invalid research prediction metadata")
        key = tuple(r[k] for k in KEY)
        if (not all(isinstance(x, str) and x for x in key)
                or next_month(r["feature_month"]) != r["label_month"]):
            raise ValueError("Invalid research sample key")
        if (r["window"] == "main" and r["label_month"] < protocol["test_start"]
                or r["window"] == "rolling" and r["label_month"] not in protocol["rolling_months"]):
            raise ValueError("Prediction is outside the declared evaluation window")
        unit = r["window"], r["model"], r["seed"]
        if (*unit, *key) in seen:
            raise ValueError("Duplicate research prediction key")
        seen.add((*unit, *key))
        if key in samples and samples[key] != r["y_true"]:
            raise ValueError("Truth differs between matched variants/windows")
        samples[key] = r["y_true"]
        groups[unit].append(r)
        monthly[(*unit, r["label_month"])].append(r)
    if len({(k[0], k[4]) for k in samples}) != 1:
        raise ValueError("Mixed research membership references")
    expected = {(w, name, seed) for w in ("main", "rolling")
                for name in VARIANTS for seed in protocol["seeds"]}
    if set(groups) != expected:
        raise ValueError("Research prediction schedule is incomplete")
    for window in ("main", "rolling"):
        units = [u for u in groups if u[0] == window]
        reference = {tuple(r[k] for k in KEY) for r in groups[units[0]]}
        for unit in units:
            if {tuple(r[k] for k in KEY) for r in groups[unit]} != reference:
                raise ValueError("Research variants must predict identical matched samples")
        if window == "rolling" and {r["label_month"] for r in groups[units[0]]} != set(protocol["rolling_months"]):
            raise ValueError("Rolling month support is incomplete")
    scores = [{"window": w, "model": name, "seed": seed, **score(values)}
              for (w, name, seed), values in sorted(groups.items())]
    by_month = [{"window": w, "model": name, "seed": seed, "month": month, **score(values)}
                for (w, name, seed, month), values in sorted(monthly.items())]
    means = []
    for window in ("main", "rolling"):
        baseline = np.mean([r["macro_f1_six"] for r in scores
                            if r["window"] == window and r["model"] == "B5_matched_boosting"])
        for name in VARIANTS:
            selected = [r for r in scores if r["window"] == window and r["model"] == name]
            value = float(np.mean([r["macro_f1_six"] for r in selected]))
            means.append(dict(window=window, model=name, n_per_seed=selected[0]["n"],
                              mean_macro_f1_six=value, delta_vs_B5=value - float(baseline),
                              mean_fallback=float(np.mean([r["fallback"] for r in selected]))))
    return dict(scores=scores, monthly=by_month, means=means,
                uncertainty=block_intervals(monthly, protocol))


def block_intervals(monthly, protocol):
    """Resample contiguous months jointly for all models and seeds.

    Six months provide only limited diagnostic information. Percentiles describe
    this resampling exercise on inspected data, not a population/unseen guarantee.
    The three-month primary holdout deliberately receives no interval.
    """
    settings = protocol["bootstrap"]
    months = protocol["rolling_months"]
    if len(months) < settings["minimum_months"]:
        return dict(status="unavailable", reason="insufficient_time_blocks")
    matrices = {key: np.asarray(score(values)["confusion"], dtype=int) for key, values in monthly.items()}
    rng = np.random.default_rng(settings["seed"])
    deltas = defaultdict(list)
    length = settings["block_length"]
    for _ in range(settings["draws"]):
        starts = rng.integers(0, len(months) - length + 1, size=math.ceil(len(months) / length))
        sampled = [months[i + j] for i in starts for j in range(length)][:len(months)]
        values = {}
        for name in VARIANTS:
            seed_values = []
            for seed in protocol["seeds"]:
                matrix = sum((matrices[("rolling", name, seed, m)] for m in sampled), np.zeros((6, 6), dtype=int))
                seed_values.append(matrix_score(matrix)["macro_f1_six"])
            values[name] = float(np.mean(seed_values))
        for name in VARIANTS:
            deltas[name].append(values[name] - values["B5_matched_boosting"])
    return dict(status="exploratory_only", main_holdout=dict(status="unavailable",
                reason="three inspected holdout months are insufficient for the six-month block policy"),
                rolling_months=months, **settings,
                intervals={name: dict(low=float(np.quantile(v, .025)), high=float(np.quantile(v, .975)))
                           for name, v in deltas.items()},
                warning="Limited six-month inspected development series; no confirmatory H3 claim")
