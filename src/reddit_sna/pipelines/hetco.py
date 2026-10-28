"""Supplementary HeTCo v1 experiment on the exact samples of a completed research run.

The research run fixes samples, labels, windows and seeds; this command adds
member node attributes from the same preparation and fits group-node attention
plus its mean-pooling ablation. Baseline rows are read, never refitted, so
every comparison is on identical keys. Scores remain inspected development
evidence, not a confirmatory test.
"""

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from reddit_sna.config import validate_run_id
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import EVENTS, KEY, matrix_score, score
from reddit_sna.evaluation.research_protocol import FULL, VARIANTS
from reddit_sna.features.members import EXTENDED_FEATURES, MEMBER_FEATURES, member_features
from reddit_sna.models.hetco import CLASS_WEIGHTS, HEADS, HETCO, fit_hetco, predict_hetco
from reddit_sna.pipelines.research import read_table, save_json, write_table


def _spec(pooling, fields, class_weight="balanced", head="flat", members="base"):
    return dict(pooling=pooling, fields=tuple(fields), class_weight=class_weight, head=head, members=members)


# Each v1 ablation removes exactly one input group from HeTCo_v1 and keeps settings.
# Entries with head=None take the (class_weight, head) pair chosen by inner validation.
MODELS = {"HeTCo_v1": _spec("attention", FULL), "A7_mean_pool": _spec("mean", FULL),
          "A1v1_no_context": _spec("attention", VARIANTS["A1_no_context"]),
          "A4v1_no_dynamics": _spec("attention", VARIANTS["A4_no_dynamics"]),
          "A6v1_no_lag": _spec("attention", VARIANTS["A6_no_lag"]),
          "HeTCo_v2": _spec("attention", FULL, None, None),
          "A7v2_mean_pool": _spec("mean", FULL, None, None),
          # v4 changes only the member attributes; head/weighting are fixed to
          # the v2 inner selection (balanced, hierarchical), so nothing is searched.
          "HeTCo_v4": _spec("attention", FULL, "balanced", "hierarchical", "extended"),
          "A7v4_mean_pool": _spec("mean", FULL, "balanced", "hierarchical", "extended")}
REFERENCES = ("B4_logreg", "B5_matched_boosting", "HeTCo_v0")
# Declared before any v2 fit; ties keep this order. Simplest candidates come first.
GRID = tuple((weight, head) for head in HEADS for weight in CLASS_WEIGHTS)


def community_delta(units, name, reference, seeds, draws=1000, seed=2026):
    """Paired bootstrap over main-window communities of the seed-mean macro-F1 difference.

    Every draw resamples the same sample keys for both models and all seeds.
    It treats communities as exchangeable within the three holdout months,
    so it ignores within-month dependence and complements the month blocks.
    """
    events = list(EVENTS)
    order = sorted(tuple(r[k] for k in KEY) for r in units[("main", reference, seeds[0])])
    position = {key: i for i, key in enumerate(order)}
    codes = {}
    for model in (name, reference):
        for s in seeds:
            truth, pred = np.zeros(len(order), int), np.zeros(len(order), int)
            for r in units[("main", model, s)]:
                i = position[tuple(r[k] for k in KEY)]
                truth[i], pred[i] = events.index(r["y_true"]), events.index(r["y_pred"])
            codes[(model, s)] = truth * 6 + pred
    rng = np.random.default_rng(seed)

    def macro(code):
        return matrix_score(np.bincount(code, minlength=36).reshape(6, 6))["macro_f1_six"]

    observed = np.mean([macro(codes[(name, s)]) for s in seeds]) - np.mean([macro(codes[(reference, s)]) for s in seeds])
    deltas = []
    for _ in range(draws):
        index = rng.integers(0, len(order), len(order))
        deltas.append(np.mean([macro(codes[(name, s)][index]) for s in seeds])
                      - np.mean([macro(codes[(reference, s)][index]) for s in seeds]))
    return dict(model=name, reference=reference, observed=float(observed),
                low=float(np.percentile(deltas, 2.5)), high=float(np.percentile(deltas, 97.5)),
                share_positive=float(np.mean(np.array(deltas) > 0)), draws=draws, unit="community")


def _fit_predict(spec, train, test, seed):
    fields, bag = spec["fields"], "bag_extended" if spec.get("members") == "extended" else "bag"
    fitted = fit_hetco([r[bag] for r in train], [[float(r[f]) for f in fields] for r in train],
                       [r["label"] for r in train], seed, spec["pooling"],
                       class_weight=spec["class_weight"], head=spec["head"])
    predicted, _, alpha = predict_hetco(fitted, [r[bag] for r in test],
                                        [[float(r[f]) for f in fields] for r in test])
    return fitted, predicted, alpha


def select_v2(samples, protocol):
    """Choose class weighting and head on inner origins strictly before test_start.

    Each origin fits label months < m and scores month m. Predictions pool over
    origins per seed; the highest seed-mean six-class macro-F1 wins.
    """
    origins = [m for m in protocol["rolling_months"] if m < protocol["test_start"]]
    if not origins:
        raise ValueError("HeTCo v2 selection needs a rolling month before the test start")
    rows = []
    for weight, head in GRID:
        spec = _spec("attention", FULL, weight, head)
        values = []
        for seed in protocol["seeds"]:
            pooled = []
            for month in origins:
                train = [r for r in samples if r["label_month"] < month]
                test = [r for r in samples if r["label_month"] == month]
                _, predicted, _ = _fit_predict(spec, train, test, seed)
                pooled += [dict(y_true=r["label"], y_pred=p, fallback=0) for r, p in zip(test, predicted)]
            values.append(score(pooled)["macro_f1_six"])
        rows.append(dict(class_weight=weight, head=head, origins=" ".join(origins),
                         mean_macro_f1_six=float(np.mean(values))))
    best = max(rows, key=lambda r: r["mean_macro_f1_six"])
    return rows, (best["class_weight"], best["head"])


def _block_delta(monthly, months, name, reference, seeds, settings):
    """Joint contiguous-month resampling of the seed-mean macro-F1 difference."""
    matrices = {k: np.asarray(score(v)["confusion"]) for k, v in monthly.items()}
    rng = np.random.default_rng(settings["seed"])
    length, deltas = settings["block_length"], []
    for _ in range(settings["draws"]):
        starts = rng.integers(0, len(months) - length + 1, size=-(-len(months) // length))
        sampled = [months[i + j] for i in starts for j in range(length)][:len(months)]
        values = []
        for model in (name, reference):
            values.append(np.mean([matrix_score(sum(matrices[(model, seed, m)] for m in sampled))["macro_f1_six"]
                                   for seed in seeds]))
        deltas.append(values[0] - values[1])
    return dict(model=name, reference=reference, low=float(np.percentile(deltas, 2.5)),
                high=float(np.percentile(deltas, 97.5)), share_positive=float(np.mean(np.array(deltas) > 0)))


def load_samples(research_run, preparation, extended=False):
    """Research samples with each community's past-only member attribute bag.

    With `extended`, `bag_extended` adds EXTENDED_FEATURES after the base columns.
    """
    samples = read_table(research_run / "samples.csv")
    detection = json.loads((preparation / "detection.json").read_text(encoding="utf-8"))
    months = sorted({r["feature_month"] for r in samples})
    groups = {}
    for month in months:
        groups[month] = defaultdict(set)
        for r in read_table(preparation / f"memberships/{month}/membership-seed{detection['canonical_seed']}.csv"):
            groups[month][r["community_id"]].add(r["user_id"])
    bags = member_features(preparation / "normalized.sqlite", preparation / "snapshots", months, groups,
                           extended=extended)
    width = len(MEMBER_FEATURES)
    for r in samples:
        full = np.asarray(bags[(r["feature_month"], r["community_id"])])
        r["bag"] = full[:, :width]
        if extended:
            r["bag_extended"] = full
    return samples


def run_hetco(research_run, preparation, artifact_root, run_id, models=None):
    """`models` optionally restricts the run to a subset of MODELS (default: all)."""
    started = perf_counter()
    models = {name: dict(MODELS[name]) for name in (models or MODELS)}
    research_run, preparation, artifact_root = (Path(p).resolve() for p in (research_run, preparation, artifact_root))
    validate_run_id(run_id)
    output = artifact_root / "hetco" / run_id
    if output.exists() or not output.is_relative_to(artifact_root):
        raise ValueError("HeTCo output exists or escapes artifacts")
    source = json.loads((research_run / "manifest.json").read_text(encoding="utf-8"))
    if source.get("status") != "complete" or Path(source["source_preparation"]).resolve() != preparation:
        raise ValueError("HeTCo needs a complete research run built from this preparation")
    protocol = json.loads((research_run / "protocol.json").read_text(encoding="utf-8"))
    pins = {str(p): digest_file(p) for p in (research_run / "manifest.json", preparation / "manifest.json")}
    output.mkdir(parents=True)
    manifest = dict(status="started", schema_version=1, artifact_type="hetco-v1",
                    source_manifests=pins, settings=HETCO, member_features=list(MEMBER_FEATURES),
                    models={k: {**v, "fields": list(v["fields"])} for k, v in models.items()},
                    selection_grid=[list(g) for g in GRID], references=list(REFERENCES),
                    exposure="inspected_development_data", unseen=False,
                    scope="lightweight group-node attention after Revelle et al. 2021; not the full original GNN")
    save_json(output / "manifest.json", manifest)
    try:
        samples = load_samples(research_run, preparation,
                               extended=any(s.get("members") == "extended" for s in models.values()))
        if any(spec["head"] is None for spec in models.values()):
            selection, (weight, head) = select_v2(samples, protocol)
            write_table(output / "selection.csv", selection)
            for spec in models.values():
                if spec["head"] is None:
                    spec.update(class_weight=weight, head=head)
            manifest.update(selected=dict(class_weight=weight, head=head),
                            models={k: {**v, "fields": list(v["fields"])} for k, v in models.items()})
            save_json(output / "manifest.json", manifest)
        windows =[("main", protocol["test_start"]), *[("rolling", m) for m in protocol["rolling_months"]]]
        predictions, fits, attention = [], [], []
        # Attention profile of the newest attention model in this run.
        attended = next((n for n in ("HeTCo_v4", "HeTCo_v2", "HeTCo_v1") if n in models), None)
        extended = attended is not None and models[attended].get("members") == "extended"
        names = MEMBER_FEATURES + EXTENDED_FEATURES if extended else MEMBER_FEATURES
        for window, boundary in windows:
            train = [r for r in samples if r["label_month"] < boundary]
            test = [r for r in samples if (r["label_month"] >= boundary if window == "main"
                                           else r["label_month"] == boundary)]
            for seed in protocol["seeds"]:
                for name, spec in models.items():
                    fit_start = perf_counter()
                    fitted, predicted, alpha = _fit_predict(spec, train, test, seed)
                    fits.append(dict(window=window, boundary=boundary, seed=seed, model=name,
                                     train_n=len(train), test_n=len(test), final_loss=fitted["train_loss"][-1],
                                     missing_train_classes=fitted["missing_train_classes"],
                                     wall_seconds=perf_counter() - fit_start))
                    predictions.extend({**{k: r[k] for k in KEY}, "window": window, "model": name, "seed": seed,
                                        "y_true": r["label"], "y_pred": p, "fallback": 0}
                                       for r, p in zip(test, predicted))
                    if window == "main" and name == attended and seed == protocol["seeds"][0]:
                        for r, a in zip(test, alpha):
                            bag = r["bag_extended"] if extended else r["bag"]
                            attention.append(dict(feature_month=r["feature_month"], community_id=r["community_id"],
                                                  label=r["label"], size=len(a), max_attention=float(a.max()),
                                                  effective_members=float(1.0 / np.sum(a ** 2)),
                                                  **{f"weighted_{f}": float(a @ bag[:, i])
                                                     for i, f in enumerate(names)},
                                                  **{f"mean_{f}": float(bag[:, i].mean())
                                                     for i, f in enumerate(names)}))
        write_table(output / "predictions.csv", predictions)
        if attention:
            write_table(output / "attention.csv", attention)
        save_json(output / "fits.json", fits)
        reference_rows = [r for r in read_table(research_run / "predictions.csv") if r["model"] in REFERENCES]
        for r in reference_rows:
            r["seed"], r["fallback"] = int(r["seed"]), int(r["fallback"])
        combined = reference_rows + predictions
        units, monthly = defaultdict(list), defaultdict(list)
        for r in combined:
            units[(r["window"], r["model"], r["seed"])].append(r)
            if r["window"] == "rolling":
                monthly[(r["model"], r["seed"], r["label_month"])].append(r)
        for window in ("main", "rolling"):
            keys = {frozenset(tuple(r[k] for k in KEY) for r in rows)
                    for (w, _, _), rows in units.items() if w == window}
            if len(keys) != 1:
                raise ValueError("HeTCo and reference predictions must cover identical samples")
        comparison = []
        for window in ("main", "rolling"):
            for name in (*REFERENCES, *models):
                values = [score(units[(window, name, s)]) for s in protocol["seeds"]]
                comparison.append(dict(window=window, model=name, n_per_seed=values[0]["n"],
                                       mean_macro_f1_six=float(np.mean([v["macro_f1_six"] for v in values])),
                                       mean_balanced_accuracy=float(np.mean([v["balanced_accuracy"] for v in values]))))
        monthly_scores = [dict(model=m, seed=s, month=month, **{k: v for k, v in score(rows).items()
                                                                 if k in ("n", "macro_f1_six")})
                          for (m, s, month), rows in sorted(monthly.items())]
        # Full models face every reference; each ablation faces its own full model.
        bases = [n for n in ("HeTCo_v1", "HeTCo_v2", "HeTCo_v4") if n in models]
        pairs = [(name, reference) for name in bases for reference in REFERENCES]
        pairs += [(name, next((b for b in ("HeTCo_v2", "HeTCo_v4") if name.endswith(b[-2:] + "_mean_pool")),
                              "HeTCo_v1")) for name in models if name not in bases]
        pairs += [(later, earlier) for i, later in enumerate(bases) for earlier in bases[:i]]
        pairs = [(a, b) for a, b in pairs if b in models or b in REFERENCES]
        intervals = [_block_delta(monthly, protocol["rolling_months"], name, reference,
                                  protocol["seeds"], protocol["bootstrap"]) for name, reference in pairs]
        confusion = {name: score([r for s in protocol["seeds"] for r in units[("main", name, s)]])["confusion"]
                     for name in models}
        write_table(output / "comparison.csv", comparison)
        write_table(output / "monthly.csv", monthly_scores)
        main_intervals = [community_delta(units, name, reference, protocol["seeds"])
                          for name, reference in pairs]
        save_json(output / "evaluation.json", dict(comparison=comparison, intervals=intervals,
                                                   main_intervals=main_intervals,
                                                   main_confusion_pooled_seeds=confusion))
        if any(digest_file(Path(p)) != h for p, h in pins.items()):
            raise ValueError("HeTCo sources changed during execution")
        manifest.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat(),
                        wall_seconds=perf_counter() - started,
                        artifact_hashes={p.name: digest_file(p) for p in output.iterdir()
                                         if p.is_file() and p.name != "manifest.json"})
        save_json(output / "manifest.json", manifest)
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__, wall_seconds=perf_counter() - started)
        save_json(output / "manifest.json", manifest)
        raise
    return output
