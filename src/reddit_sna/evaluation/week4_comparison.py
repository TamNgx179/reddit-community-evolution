"""General comparative evaluation module for Week 4 deliverables.

Fulfills Week 4 requirements:
1. Primary benchmark table across 5 reference baselines, HGB/LR comparators,
   proposed model, and ablation controls (Macro-F1 per seed, Mean, SD, Accuracy).
2. Per-class metrics (highlighting grow/merge, to_dissolve) and per-month metrics.
3. Paired wins/losses across multiple comparator models decomposed by seed, class, and month.
4. Target cases evaluation (repaired, broken, confusion) with strict pre-declaration gates.
5. Automated reconciliation against frozen handoff verification files.
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reddit_sna.evaluation.diagnostics import (
    EVENTS,
    KEY,
    prediction_units,
    score,
)

# Standard evaluation role mapping
MODEL_ROLE_MAP: dict[str, str] = {
    "hier_lr_dynamic": "Proposed Baseline (Hierarchical LR Dynamic)",
    "hier_hgb_dynamic": "Reference Comparator (Hierarchical HGB Dynamic)",
    "flat_lr_dynamic": "Linear Comparator (Flat LR Dynamic)",
    "B4_logreg": "Linear Baseline (Logistic Regression)",
    "B2_random_forest": "Tree Baseline (Random Forest)",
    "B5_matched_boosting": "Tree Baseline (Matched Boosting HGB)",
    "B1_majority": "Trivial Baseline (Majority)",
    "B1_persistence": "Heuristic Baseline (Persistence)",
    "A_no_context_drift_matched": "Ablation Control (No Context Drift Matched)",
    "hier_hgb_static": "Control (Hierarchical HGB Static)",
    "A_no_dynamics_matched": "Ablation Control (No Dynamics Matched)",
    "flat_hgb_dynamic": "Ablation Baseline (Flat HGB Dynamic)",
    "hier_lr_static": "Control (Hierarchical LR Static)",
    "flat_hgb_static": "Control (Flat HGB Static)",
    "A_flat_matched": "Ablation Control (Flat Matched)",
    "flat_lr_static": "Control (Flat LR Static)",
    "flat_lr_SHL": "Feature Control (Flat LR SHL)",
    "flat_hgb_SHL": "Feature Control (Flat HGB SHL)",
    "HeTCo_v0": "Historical Pilot (HeTCo v0)",
}

DEFAULT_EXPECTED_MODELS: tuple[str, ...] = (
    "hier_lr_dynamic",
    "hier_hgb_dynamic",
    "flat_lr_dynamic",
    "B4_logreg",
    "B2_random_forest",
    "B5_matched_boosting",
    "B1_majority",
    "B1_persistence",
    "A_no_context_drift_matched",
    "hier_hgb_static",
    "A_no_dynamics_matched",
    "flat_hgb_dynamic",
    "hier_lr_static",
    "flat_hgb_static",
    "A_flat_matched",
    "flat_lr_static",
    "flat_lr_SHL",
    "flat_hgb_SHL",
    "HeTCo_v0",
)


def compute_primary_comparison_table(
    predictions: list[dict[str, Any]],
    proposed_model: str = "hier_lr_dynamic",
    expected_models: tuple[str, ...] = DEFAULT_EXPECTED_MODELS,
    seeds: tuple[int, ...] = (42, 43, 44),
    window: str = "final",
) -> tuple[pd.DataFrame, list[str]]:
    """Build the primary comparison table across baselines, comparators, and proposed.

    Args:
        predictions: Prediction rows.
        proposed_model: Name of the proposed model to evaluate.
        expected_models: Ordered tuple of expected benchmark models.
        seeds: Random evaluation seeds.
        window: Prediction window tag.

    Returns:
        tuple of (summary_df, missing_models_list)
    """
    avail_models = {r["model"] for r in predictions}
    if proposed_model not in avail_models:
        raise ValueError(
            f"Proposed model '{proposed_model}' not found in predictions dataset. "
            f"Available models: {sorted(avail_models)}"
        )

    # Compile target models list ensuring proposed_model is included first
    ordered_models: list[str] = [proposed_model]
    for m in expected_models:
        if m != proposed_model and m not in ordered_models:
            ordered_models.append(m)

    missing_models: list[str] = [m for m in ordered_models if m not in avail_models]
    present_models: list[str] = [m for m in ordered_models if m in avail_models]

    units = prediction_units(predictions)

    summary_rows: list[dict[str, Any]] = []
    for model in present_models:
        seed_f1s: dict[int, float] = {}
        seed_accs: dict[int, float] = {}
        n_per_seed: int = 0

        for seed in seeds:
            unit_key = (window, model, seed)
            if unit_key not in units:
                continue
            rows = list(units[unit_key].values())
            n_per_seed = len(rows)
            sc = score(rows)
            matrix = np.asarray(sc["confusion"], dtype=int)
            acc = float(np.trace(matrix) / n_per_seed) if n_per_seed > 0 else 0.0
            seed_f1s[seed] = float(sc["macro_f1_six"])
            seed_accs[seed] = acc

        f1_vals = [seed_f1s[s] for s in seeds if s in seed_f1s]
        acc_vals = [seed_accs[s] for s in seeds if s in seed_accs]

        mean_f1 = float(np.mean(f1_vals)) if f1_vals else 0.0
        sd_f1 = float(np.std(f1_vals, ddof=1)) if len(f1_vals) > 1 else 0.0
        mean_acc = float(np.mean(acc_vals)) if acc_vals else 0.0

        if model == proposed_model:
            role = f"Proposed ({proposed_model})"
        else:
            role = MODEL_ROLE_MAP.get(model, "Benchmark Control")

        row_dict: dict[str, Any] = {
            "model": model,
            "role": role,
            "n_per_seed": n_per_seed,
            "macro_f1_mean": round(mean_f1, 4),
            "macro_f1_sd": round(sd_f1, 4),
            "accuracy_mean": round(mean_acc, 4),
        }
        for s in seeds:
            row_dict[f"macro_f1_seed_{s}"] = round(seed_f1s.get(s, 0.0), 4)

        summary_rows.append(row_dict)

    summary_df = pd.DataFrame(summary_rows)
    return summary_df, missing_models


def compute_per_class_and_monthly_tables(
    predictions: list[dict[str, Any]],
    models: list[str],
    seeds: tuple[int, ...] = (42, 43, 44),
    window: str = "final",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate per-class metrics and monthly Macro-F1 breakdown per model.

    Args:
        predictions: Prediction rows.
        models: List of model names to calculate.
        seeds: Random seeds to evaluate and average.
        window: Window tag.

    Returns:
        tuple of (per_class_df, per_month_df)
    """
    units = prediction_units(predictions)
    dissolve_idx = EVENTS.index("dissolve")

    per_class_rows: list[dict[str, Any]] = []
    per_month_rows: list[dict[str, Any]] = []

    for model in models:
        # 1. Per-class metrics across seeds
        seed_class_stats: collections.defaultdict[str, list[dict[str, Any]]] = collections.defaultdict(list)

        # 2. Per-month metrics across seeds
        seed_month_stats: collections.defaultdict[str, list[dict[str, Any]]] = collections.defaultdict(list)

        for seed in seeds:
            unit_key = (window, model, seed)
            if unit_key not in units:
                continue
            rows = units[unit_key]

            # Overall confusion matrix
            all_rows = list(rows.values())
            sc_all = score(all_rows)
            matrix = np.asarray(sc_all["confusion"], dtype=int)

            for i, event in enumerate(EVENTS):
                support = int(matrix[i].sum())
                predicted = int(matrix[:, i].sum())
                true_positive = int(matrix[i, i])
                to_dissolve = int(matrix[i, dissolve_idx])

                precision = (true_positive / predicted) if predicted else 0.0
                recall = (true_positive / support) if support else 0.0
                f1 = (
                    (2 * precision * recall / (precision + recall))
                    if (precision + recall)
                    else 0.0
                )

                seed_class_stats[event].append({
                    "support": support,
                    "predicted": predicted,
                    "true_positive": true_positive,
                    "to_dissolve": to_dissolve,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                })

            # Monthly breakdown
            months = sorted({k[3] for k in rows})
            for m in months:
                m_rows = [r for k, r in rows.items() if k[3] == m]
                sc_m = score(m_rows)
                m_matrix = np.asarray(sc_m["confusion"], dtype=int)
                acc = float(np.trace(m_matrix) / len(m_rows)) if m_rows else 0.0
                seed_month_stats[m].append({
                    "n": len(m_rows),
                    "macro_f1": float(sc_m["macro_f1_six"]),
                    "accuracy": acc,
                })

        # Average class stats over seeds
        for event in EVENTS:
            c_records = seed_class_stats[event]
            if not c_records:
                continue
            mean_supp = int(round(np.mean([r["support"] for r in c_records])))
            mean_pred = int(round(np.mean([r["predicted"] for r in c_records])))
            mean_to_diss = int(round(np.mean([r["to_dissolve"] for r in c_records])))
            mean_rec = float(np.mean([r["recall"] for r in c_records]))
            mean_f1 = float(np.mean([r["f1"] for r in c_records]))
            mean_prec = float(np.mean([r["precision"] for r in c_records]))

            diss_rate = (mean_to_diss / mean_supp) if mean_supp > 0 else 0.0

            per_class_rows.append({
                "model": model,
                "label": event,
                "support": mean_supp,
                "predicted": mean_pred,
                "to_dissolve": mean_to_diss,
                "to_dissolve_rate": round(diss_rate, 4),
                "recall": round(mean_rec, 4),
                "precision": round(mean_prec, 4),
                "f1": round(mean_f1, 4),
            })

        # Average monthly stats over seeds
        for m, m_records in seed_month_stats.items():
            mean_n = int(round(np.mean([r["n"] for r in m_records])))
            mean_mf1 = float(np.mean([r["macro_f1"] for r in m_records]))
            mean_macc = float(np.mean([r["accuracy"] for r in m_records]))

            per_month_rows.append({
                "model": model,
                "label_month": m,
                "support": mean_n,
                "macro_f1": round(mean_mf1, 4),
                "accuracy": round(mean_macc, 4),
            })

    per_class_df = pd.DataFrame(per_class_rows)
    per_month_df = pd.DataFrame(per_month_rows)
    return per_class_df, per_month_df


def compute_paired_wins_losses(
    predictions: list[dict[str, Any]],
    proposed_model: str,
    comparator_models: list[str],
    seeds: tuple[int, ...] = (42, 43, 44),
    window: str = "final",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """Compute paired wins/losses for proposed vs multiple comparator models.

    Args:
        predictions: Prediction rows.
        proposed_model: Name of proposed model.
        comparator_models: List of comparator model names.
        seeds: Random evaluation seeds.
        window: Window tag.

    Returns:
        tuple of:
            - summary_df: Overall wins/losses/net per comparator and seed.
            - by_class_df: Decomposed wins/losses by true event class.
            - by_month_df: Decomposed wins/losses by label_month.
            - case_details_dict: Dictionary mapping comparator -> DataFrame of all paired cases.
    """
    units = prediction_units(predictions)

    avail_models = {r["model"] for r in predictions}
    if proposed_model not in avail_models:
        raise ValueError(f"Proposed model '{proposed_model}' not found in predictions.")

    valid_comparators = [c for c in comparator_models if c in avail_models and c != proposed_model]

    summary_rows: list[dict[str, Any]] = []
    by_class_rows: list[dict[str, Any]] = []
    by_month_rows: list[dict[str, Any]] = []
    case_details_dict: dict[str, pd.DataFrame] = {}

    for comp in valid_comparators:
        comp_cases: list[dict[str, Any]] = []

        for seed in seeds:
            p_key = (window, proposed_model, seed)
            c_key = (window, comp, seed)
            if p_key not in units or c_key not in units:
                continue

            p_rows = units[p_key]
            c_rows = units[c_key]

            # Track counts
            both_correct = 0
            wins = 0  # proposed correct, comparator wrong
            losses = 0  # comparator correct, proposed wrong
            both_wrong = 0

            class_counter: collections.defaultdict[str, collections.defaultdict[str, int]] = collections.defaultdict(
                lambda: collections.defaultdict(int)
            )
            month_counter: collections.defaultdict[str, collections.defaultdict[str, int]] = collections.defaultdict(
                lambda: collections.defaultdict(int)
            )

            for key in sorted(p_rows):
                p_item = p_rows[key]
                c_item = c_rows[key]

                yt = p_item["y_true"]
                month = key[3]

                p_correct = (p_item["y_pred"] == yt)
                c_correct = (c_item["y_pred"] == yt)

                if p_correct and c_correct:
                    outcome = "both_correct"
                    both_correct += 1
                elif p_correct and not c_correct:
                    outcome = "proposed_only"
                    wins += 1
                elif not p_correct and c_correct:
                    outcome = "reference_only"
                    losses += 1
                else:
                    outcome = "both_wrong"
                    both_wrong += 1

                class_counter[yt][outcome] += 1
                month_counter[month][outcome] += 1

                case_dict = dict(zip(KEY, key))
                case_dict.update({
                    "seed": seed,
                    "proposed_model": proposed_model,
                    "comparator_model": comp,
                    "y_true": yt,
                    "proposed_prediction": p_item["y_pred"],
                    "comparator_prediction": c_item["y_pred"],
                    "outcome": outcome,
                    "prediction_disagreement": int(p_item["y_pred"] != c_item["y_pred"]),
                    "size": p_item.get("size", "N/A"),
                })
                comp_cases.append(case_dict)

            net = wins - losses
            summary_rows.append({
                "proposed_model": proposed_model,
                "comparator_model": comp,
                "seed": seed,
                "total_cases": len(p_rows),
                "both_correct": both_correct,
                "proposed_only (wins)": wins,
                "reference_only (losses)": losses,
                "both_wrong": both_wrong,
                "net_wins": net,
            })

            for event in EVENTS:
                c_cnt = class_counter[event]
                w = c_cnt["proposed_only"]
                l = c_cnt["reference_only"]
                by_class_rows.append({
                    "proposed_model": proposed_model,
                    "comparator_model": comp,
                    "seed": seed,
                    "y_true": event,
                    "both_correct": c_cnt["both_correct"],
                    "wins": w,
                    "losses": l,
                    "both_wrong": c_cnt["both_wrong"],
                    "net": w - l,
                })

            for m in sorted(month_counter):
                m_cnt = month_counter[m]
                w = m_cnt["proposed_only"]
                l = m_cnt["reference_only"]
                by_month_rows.append({
                    "proposed_model": proposed_model,
                    "comparator_model": comp,
                    "seed": seed,
                    "label_month": m,
                    "both_correct": m_cnt["both_correct"],
                    "wins": w,
                    "losses": l,
                    "both_wrong": m_cnt["both_wrong"],
                    "net": w - l,
                })

        case_details_dict[comp] = pd.DataFrame(comp_cases)

    summary_df = pd.DataFrame(summary_rows)
    by_class_df = pd.DataFrame(by_class_rows)
    by_month_df = pd.DataFrame(by_month_rows)

    return summary_df, by_class_df, by_month_df, case_details_dict


def evaluate_target_cases(
    predictions: list[dict[str, Any]],
    target_cases_keys: set[tuple[str, ...]] | None = None,
    proposed_model: str = "hier_lr_dynamic",
    old_proposed_model: str = "hier_lr_dynamic",
    canonical_seed: int = 42,
    window: str = "final",
) -> dict[str, Any]:
    """Re-evaluate target cases for repair and degradation against declared keys.

    If target_cases_keys is None, strictly falls back to the descriptive 34 grow/merge cases,
    tagging it as 'DESCRIPTIVE ONLY - target set not pre-declared by owner'.
    """
    units = prediction_units(predictions)

    p_key = (window, proposed_model, canonical_seed)
    old_key = (window, old_proposed_model, canonical_seed)

    if p_key not in units:
        raise ValueError(f"Model '{proposed_model}' seed {canonical_seed} not found in predictions.")
    if old_key not in units:
        raise ValueError(f"Old baseline model '{old_proposed_model}' seed {canonical_seed} not found in predictions.")

    p_rows = units[p_key]
    old_rows = units[old_key]

    if target_cases_keys is not None:
        # Pre-declared target cases provided
        matched_keys = [k for k in target_cases_keys if k in p_rows and k in old_rows]
        n_cases = len(matched_keys)

        correct_old = 0
        correct_new = 0
        repaired = 0  # old wrong -> new correct
        broken = 0  # old correct -> new wrong

        conf_old = collections.defaultdict(lambda: collections.defaultdict(int))
        conf_new = collections.defaultdict(lambda: collections.defaultdict(int))

        for k in matched_keys:
            old_item = old_rows[k]
            new_item = p_rows[k]

            yt = old_item["y_true"]
            old_pred = old_item["y_pred"]
            new_pred = new_item["y_pred"]

            old_ok = (old_pred == yt)
            new_ok = (new_pred == yt)

            if old_ok:
                correct_old += 1
            if new_ok:
                correct_new += 1

            if not old_ok and new_ok:
                repaired += 1
            elif old_ok and not new_ok:
                broken += 1

            conf_old[yt][old_pred] += 1
            conf_new[yt][new_pred] += 1

        return {
            "provided": True,
            "is_descriptive_only": False,
            "label": "Pre-declared Target Set Evaluation",
            "total_cases": n_cases,
            "correct_old": correct_old,
            "correct_new": correct_new,
            "repaired_cases": repaired,
            "broken_cases": broken,
            "confusion_old": {k: dict(v) for k, v in conf_old.items()},
            "confusion_new": {k: dict(v) for k, v in conf_new.items()},
        }
    else:
        # Fallback to 34 grow/merge cases descriptive summary
        grow_merge_keys = [k for k, r in old_rows.items() if r["y_true"] in ("grow", "merge")]
        n_gm = len(grow_merge_keys)

        correct_old = 0
        correct_new = 0
        repaired = 0
        broken = 0

        dissolve_old = 0
        dissolve_new = 0

        breakdown: collections.defaultdict[str, dict[str, int]] = collections.defaultdict(lambda: {
            "support": 0, "correct_old": 0, "correct_new": 0, "dissolve_old": 0, "dissolve_new": 0
        })

        for k in grow_merge_keys:
            old_item = old_rows[k]
            new_item = p_rows[k]

            yt = old_item["y_true"]
            old_pred = old_item["y_pred"]
            new_pred = new_item["y_pred"]

            old_ok = (old_pred == yt)
            new_ok = (new_pred == yt)

            if old_ok:
                correct_old += 1
            if new_ok:
                correct_new += 1

            if not old_ok and new_ok:
                repaired += 1
            elif old_ok and not new_ok:
                broken += 1

            if old_pred == "dissolve":
                dissolve_old += 1
            if new_pred == "dissolve":
                dissolve_new += 1

            b = breakdown[yt]
            b["support"] += 1
            if old_ok:
                b["correct_old"] += 1
            if new_ok:
                b["correct_new"] += 1
            if old_pred == "dissolve":
                b["dissolve_old"] += 1
            if new_pred == "dissolve":
                b["dissolve_new"] += 1

        return {
            "provided": False,
            "is_descriptive_only": True,
            "label": "DESCRIPTIVE ONLY - target set not pre-declared by owner",
            "total_cases": n_gm,
            "correct_old": correct_old,
            "correct_new": correct_new,
            "repaired_cases": repaired,
            "broken_cases": broken,
            "dissolve_predicted_old": dissolve_old,
            "dissolve_predicted_new": dissolve_new,
            "breakdown": dict(breakdown),
        }


def reconcile_week4_reproducibility(
    predictions: list[dict[str, Any]],
    handoff_dir: Path | None,
    proposed_model: str = "hier_lr_dynamic",
    canonical_seed: int = 42,
    window: str = "final",
) -> dict[str, Any]:
    """Verify exact 4-group distribution, contrast keys, and F1 reproducibility."""
    units = prediction_units(predictions)
    p_key = (window, proposed_model, canonical_seed)
    h_key = (window, "hier_hgb_dynamic", canonical_seed)

    if p_key not in units or h_key not in units:
        return {"status": "FAIL", "reason": "Missing proposed or reference prediction units"}

    p_rows = units[p_key]
    h_rows = units[h_key]

    both_correct = 0
    proposed_only = 0
    hgb_only = 0
    both_wrong = 0
    diff_keys: set[tuple[str, ...]] = set()

    for k, p_item in p_rows.items():
        h_item = h_rows[k]
        yt = p_item["y_true"]
        pc = (p_item["y_pred"] == yt)
        hc = (h_item["y_pred"] == yt)

        if pc and hc:
            both_correct += 1
        elif pc and not hc:
            proposed_only += 1
            diff_keys.add(k)
        elif not pc and hc:
            hgb_only += 1
            diff_keys.add(k)
        else:
            both_wrong += 1

    # Check Macro-F1
    sc_p = score(list(p_rows.values()))
    sc_h = score(list(h_rows.values()))

    p_f1 = float(sc_p["macro_f1_six"])
    h_f1 = float(sc_h["macro_f1_six"])

    c64_match = False
    c64_file = None

    # Check against correctness_contrast_64 if present
    candidates: list[Path] = []
    if handoff_dir and handoff_dir.is_dir():
        candidates.extend([
            handoff_dir / "correctness_contrast_64_seed42.csv",
            handoff_dir / "reproduced/correctness_contrast_64_seed42.csv",
            handoff_dir.parent / "tam-final-1269/correctness_contrast_64_seed42.csv",
            handoff_dir.parent / "tam-final-1269/reproduced/correctness_contrast_64_seed42.csv",
        ])
    c64_file = next((p for p in candidates if p.is_file()), None)
    if c64_file:
        with c64_file.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            expected_keys = {tuple(row[k] for k in KEY) for row in r}
            c64_match = (expected_keys == diff_keys)

    expected_4group = (both_correct == 1119 and proposed_only == 29 and hgb_only == 35 and both_wrong == 86)
    f1_match = (abs(p_f1 - 0.4117) < 1e-3 and abs(h_f1 - 0.3880) < 1e-3)

    overall_pass = expected_4group and f1_match
    if c64_file:
        overall_pass = overall_pass and c64_match

    return {
        "status": "PASS" if overall_pass else "FAIL",
        "both_correct": both_correct,
        "proposed_only": proposed_only,
        "hgb_only": hgb_only,
        "both_wrong": both_wrong,
        "contrast_cases": len(diff_keys),
        "expected_4group_pass": expected_4group,
        "f1_match_pass": f1_match,
        "c64_checked": c64_file is not None,
        "c64_keys_match": c64_match,
        "proposed_macro_f1": round(p_f1, 4),
        "hgb_macro_f1": round(h_f1, 4),
    }
