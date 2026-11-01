"""Read-only error-mechanism audit of the proposed model on the 2015 HeTCo pilot.

Joins stored predictions of HeTCo_v4 (proposed) with HGB (B5), LR (B4), the
flat head (HeTCo_v1), the no-D ablation (A4v1_no_dynamics) and mean pooling on
identical keys. Nothing is fitted, thresholded or relabelled. Every lineage
quantity is taken from the t-1 -> t GED inclusion pairs, so it is available at
feature month t. Outputs go to a new directory under artifacts/diagnostics.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

KEY = ["reference_id", "feature_month", "community_id", "label_month", "label_reference_id"]
EVENTS = ["dissolve", "grow", "shrink", "merge", "split", "stable"]
SEEDS = [42, 43, 44]
# model name -> run that stored its predictions
SOURCES = {
    "HeTCo_v4": "hetco/hetco-v4-001", "A7v4_mean_pool": "hetco/hetco-v4-001",
    "HeTCo_v2": "hetco/hetco-v4-001", "HeTCo_v1": "hetco/hetco-v1-002",
    "A4v1_no_dynamics": "hetco/hetco-v1-002", "B4_logreg": "research/midterm-thanh-001",
    "B5_matched_boosting": "research/midterm-thanh-001", "HeTCo_v0": "research/midterm-thanh-001",
    "A4_no_dynamics": "research/midterm-thanh-001",
}
PROPOSED, HGB = "HeTCo_v4", "B5_matched_boosting"


def macro_f1(truth, pred):
    return f1_score(truth, pred, labels=EVENTS, average="macro", zero_division=0)


def size_band(size):
    return "2" if size <= 2 else "3-4" if size <= 4 else "5-20" if size <= 20 else ">20"


def load(root):
    frames = []
    for model, run in SOURCES.items():
        p = pd.read_csv(root / run / "predictions.csv")
        frames.append(p[p.model == model])
    preds = pd.concat(frames, ignore_index=True)
    samples = pd.read_csv(root / "research/midterm-thanh-001/samples.csv")
    pairs = pd.read_csv(root / "core/forecast-ged-history-v3/inclusion_pairs.csv")
    # Strongest incoming overlap of each community at t from the t-1 -> t pairs.
    incoming = (pairs.groupby(["label_month", "target_community_id"])
                .agg(max_backward=("inclusion_backward", "max"), max_forward=("inclusion_forward", "max"),
                     max_shared=("shared_members", "max"))
                .reset_index().rename(columns={"label_month": "feature_month",
                                               "target_community_id": "community_id"}))
    samples = samples.merge(incoming, on=["feature_month", "community_id"], how="left")
    for col in ("max_backward", "max_forward", "max_shared"):
        samples[col] = samples[col].fillna(0.0)
    samples["max_shared_fraction"] = samples.max_shared / samples["size"]
    first = samples.feature_month.min()
    # Zones follow the tracker's own thresholds: dissolve=0.1, beta=0.5.
    samples["history_state"] = np.select(
        [samples.feature_month == first, samples.history_missing == 0,
         samples.max_shared == 0, samples.max_backward < 0.1],
        ["left_censored", "observed", "missing_no_shared", "missing_below_0.1"], "missing_0.1_to_beta")
    samples["lineage_reset"] = ((samples.history_missing == 0) & (samples.community_age == 1)).astype(int)
    samples["size_band"] = samples["size"].map(size_band)
    return preds, samples


def wide(preds, samples, window):
    w = preds[preds.window == window].pivot_table(index=KEY + ["seed", "y_true"], columns="model",
                                                    values="y_pred", aggfunc="first").reset_index()
    w = w.merge(samples.drop(columns=["label"]), on=KEY, how="left", validate="many_to_one")
    if w.history_state.isna().any():
        raise ValueError("Prediction keys missing from samples")
    return w


def tier_table(w, models):
    rows = []
    for model in models:
        for seed, g in w.groupby("seed"):
            t, p = g.y_true, g[model]
            nd_true, nd_pred = t != "dissolve", p != "dissolve"
            rows.append(dict(model=model, seed=seed, n=len(g), macro_f1=macro_f1(t, p),
                             tier1_missed_event=int((nd_true & ~nd_pred).sum()),
                             tier1_false_event=int((~nd_true & nd_pred).sum()),
                             tier2_wrong_event=int((nd_true & nd_pred & (t != p)).sum()),
                             events_true=int(nd_true.sum()),
                             grow_to_dissolve=int(((t == "grow") & (p == "dissolve")).sum()),
                             merge_to_dissolve=int(((t == "merge") & (p == "dissolve")).sum()),
                             grow_n=int((t == "grow").sum()), merge_n=int((t == "merge").sum())))
    return pd.DataFrame(rows)


def strata_table(w, models, by):
    rows = []
    for model in models:
        for (level, seed), g in w.groupby([by, "seed"]):
            nd = g.y_true != "dissolve"
            rows.append(dict(model=model, stratum=by, level=level, seed=seed, n=len(g),
                             events_true=int(nd.sum()),
                             event_recall_tier1=float((g[model][nd] != "dissolve").mean()) if nd.any() else np.nan,
                             exact_event_recall=float((g[model][nd] == g.y_true[nd]).mean()) if nd.any() else np.nan,
                             dissolve_false_alarm=float((g[model][~nd] != "dissolve").mean()) if (~nd).any() else np.nan,
                             macro_f1=macro_f1(g.y_true, g[model])))
    out = pd.DataFrame(rows)
    return out.groupby(["model", "stratum", "level"]).agg(
        n=("n", "first"), events_true=("events_true", "first"),
        event_recall_tier1=("event_recall_tier1", "mean"), exact_event_recall=("exact_event_recall", "mean"),
        dissolve_false_alarm=("dissolve_false_alarm", "mean"), macro_f1=("macro_f1", "mean"),
        macro_f1_seed_sd=("macro_f1", "std")).reset_index()


def seed_table(w, models):
    case = w.groupby(KEY + ["y_true", "history_state", "size_band"])
    rows = []
    for model in models:
        flips = case[model].nunique()
        frame = flips.reset_index(name="distinct")
        for (truth_group, level), g in frame.assign(
                truth_group=np.where(frame.y_true == "dissolve", "dissolve", "event")).groupby(["truth_group", "size_band"]):
            rows.append(dict(model=model, truth=truth_group, size_band=level, cases=len(g),
                             unstable_cases=int((g.distinct > 1).sum())))
        rows.append(dict(model=model, truth="all", size_band="all", cases=len(frame),
                         unstable_cases=int((frame.distinct > 1).sum())))
    return pd.DataFrame(rows)


def paired_table(w):
    ok_p, ok_h = w[PROPOSED] == w.y_true, w[HGB] == w.y_true
    w = w.assign(group=np.select([ok_p & ok_h, ok_p & ~ok_h, ~ok_p & ok_h], ["both_correct", "proposed_only",
                                                                           "hgb_only"], "both_wrong"))
    return (w.groupby(["seed", "group", "history_state"]).size().unstack("history_state", fill_value=0)
            .reset_index())


def case_table(w):
    target = w[w.y_true.isin(["grow", "merge"])]
    models = list(SOURCES)
    rows = []
    for key, g in target.groupby(KEY):
        g = g.set_index("seed")
        first = g.iloc[0]
        row = dict(zip(KEY, key))
        row.update({c: first[c] for c in ("y_true", "size", "community_age", "history_missing", "predecessor_count",
                                           "history_state", "lineage_reset", "max_backward", "max_shared_fraction",
                                           "past_retention", "lag_missing", "thread_activity")})
        for model in models:
            row[model] = "/".join(g.loc[s, model] for s in SEEDS)
        row["proposed_dissolve_seeds"] = int(sum(g.loc[s, PROPOSED] == "dissolve" for s in SEEDS))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["y_true", "proposed_dissolve_seeds", "size"], ascending=[True, False, False])


def attention_table(root, w):
    att = pd.read_csv(root / "hetco/hetco-v4-001/attention.csv")
    keys = w[w.seed == SEEDS[0]][["feature_month", "community_id", "size_band", "history_state"]]
    att = att.merge(keys, on=["feature_month", "community_id"], how="inner")
    att["effective_share"] = att.effective_members / att["size"]
    flips = w.groupby(["feature_month", "community_id"])[PROPOSED].nunique().rename("distinct").reset_index()
    att = att.merge(flips, on=["feature_month", "community_id"])
    return att.groupby("size_band").agg(cases=("community_id", "size"), median_size=("size", "median"),
                                        median_effective_share=("effective_share", "median"),
                                        median_max_attention=("max_attention", "median"),
                                        unstable_share=("distinct", lambda d: float((d > 1).mean()))).reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    out = args.output.resolve()
    if not out.is_relative_to(root / "diagnostics"):
        raise ValueError("Output must stay under artifacts/diagnostics")
    out.mkdir(parents=True, exist_ok=False)
    preds, samples = load(root)
    models = list(SOURCES)
    tables = {}
    for window in ("main", "rolling"):
        w = wide(preds, samples, window)
        tables[f"{window}_tiers.csv"] = tier_table(w, models)
        tables[f"{window}_strata.csv"] = pd.concat([strata_table(w, models, by)
                                                    for by in ("history_state", "size_band", "lineage_reset")])
        tables[f"{window}_seed_stability.csv"] = seed_table(w, models)
        tables[f"{window}_paired_v4_hgb.csv"] = paired_table(w)
        tables[f"{window}_grow_merge_cases.csv"] = case_table(w)
        if window == "main":
            tables["main_attention_by_size.csv"] = attention_table(root, w)
    tables["history_by_month.csv"] = (samples.groupby(["feature_month", "history_state"]).size()
                                      .unstack(fill_value=0).reset_index())
    tables["history_by_size.csv"] = pd.crosstab([samples.size_band], samples.history_state).reset_index()
    hashes = {}
    for name, frame in tables.items():
        frame.to_csv(out / name, index=False, float_format="%.6f")
        hashes[name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    sources = {run: hashlib.sha256((root / run / "predictions.csv").read_bytes()).hexdigest()
               for run in sorted(set(SOURCES.values()))}
    (out / "manifest.json").write_text(json.dumps(dict(
        status="complete", read_only=True, fitted=False, models=SOURCES, proposed=PROPOSED, hgb=HGB,
        exposure="inspected_development_data", source_prediction_hashes=sources, outputs=hashes),
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
