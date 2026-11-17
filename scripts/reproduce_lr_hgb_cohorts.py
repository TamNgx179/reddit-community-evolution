#!/usr/bin/env python3
"""Reproduce LR-HGB comparative evaluation and paired block-bootstrap across cohorts.

Validates key and label alignment between hier_lr_dynamic and hier_hgb_dynamic,
evaluates six-class Macro-F1 across random seeds, and calculates paired block-bootstrap
confidence intervals for temporal uncertainty estimation.
"""

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from reddit_sna.evaluation.cross_cohort_comparison import (
    HGB_DEFAULT,
    LR_DEFAULT,
    paired_block_bootstrap_comparison,
    validate_paired_alignment,
)
from reddit_sna.evaluation.diagnostics import EVENTS, KEY, prediction_units
from reddit_sna.evaluation.research import matrix_score, score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduce LR-HGB comparative evaluation and paired block-bootstrap across cohorts."
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=Path("artifacts/handoff/tam-f1-20261104/export/predictions_final.csv"),
        help="Path to full-study frozen predictions CSV",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("reports/tables/sna-feedback-20261111/lr_hgb_cross_cohort_protocol.json"),
        help="Path to cross-cohort protocol JSON",
    )
    parser.add_argument(
        "--reference-intervals",
        type=Path,
        default=Path("reports/tables/sna-feedback-20261111/lr_hgb_cross_cohort_intervals.csv"),
        help="Path to reference intervals CSV for validation audit",
    )
    parser.add_argument(
        "--reference-counts",
        type=Path,
        default=Path("reports/tables/sna-feedback-20261111/lr_hgb_cross_cohort_counts.csv"),
        help="Path to reference counts CSV for validation audit",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/tables/lr_hgb_comparison_20261122"),
        help="Output directory for generated CSV tables",
    )
    parser.add_argument(
        "--draws",
        type=int,
        default=2000,
        help="Number of block-bootstrap draws (default: 2000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261031,
        help="Bootstrap random seed (default: 20261031)",
    )
    return parser.parse_args()


def compute_cohort_decision_counts(
    units: dict,
    window: str,
    model: str,
    seeds: list[int],
) -> list[dict]:
    """Compute event detection counts (hits, support, false alarms) per seed."""
    rows = []
    for s in seeds:
        sample = list(units[(window, model, s)].values())
        res = score(sample)
        mat = np.asarray(res["confusion"], dtype=int)
        # EVENTS: ('stable', 'grow', 'shrink', 'merge', 'split', 'dissolve')
        # indices: stable=0, grow=1, shrink=2, merge=3, split=4, dissolve=5
        grow_merge_support = int(mat[1].sum() + mat[3].sum())
        grow_merge_hits = int(mat[1, 1] + mat[3, 3])
        dissolve_support = int(mat[5].sum())
        # False dissolve alarms: non-dissolve communities (rows 0–4) predicted as dissolve (col 5)
        # i.e. grow/merge/shrink/split/stable predicted as dissolve — the error flagged in reports
        false_dissolve_alarms = int(mat[:5, 5].sum())

        rows.append({
            "model": model,
            "seed": s,
            "n": len(sample),
            "macro_f1": res["macro_f1_six"],
            "grow_merge_support": grow_merge_support,
            "grow_merge_hits": grow_merge_hits,
            "dissolve_support": dissolve_support,
            "false_dissolve_alarms": false_dissolve_alarms,
        })
    return rows


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("WEEK 5 REPRODUCTION: LR vs HGB COMPARISON ACROSS COHORTS")
    print("=" * 70)

    # 1. Load Protocol if present
    protocol = None
    if args.protocol.exists():
        with open(args.protocol, "r", encoding="utf-8") as f:
            protocol = json.load(f)
        print(f"Loaded protocol: {args.protocol}")
        draws = protocol.get("bootstrap", {}).get("draws", args.draws)
        b_seed = protocol.get("bootstrap", {}).get("seed", args.seed)
        block_lengths = [
            protocol.get("bootstrap", {}).get("block_length", 2),
            protocol.get("bootstrap", {}).get("sensitivity_block_length", 3),
        ]
    else:
        draws = args.draws
        b_seed = args.seed
        block_lengths = [2, 3]

    # 2. Load Full-Study Predictions
    if not args.predictions.exists():
        print(f"ERROR: Predictions file not found at {args.predictions}", file=sys.stderr)
        return 1

    print(f"Loading predictions from: {args.predictions}")
    df_preds = pd.read_csv(args.predictions, low_memory=False)
    sub_df = df_preds[df_preds["model"].isin([LR_DEFAULT, HGB_DEFAULT])]
    records = sub_df.to_dict("records")

    # 3. Alignment Audit
    print("\n--- Step 1: Validating Model Key & Label Alignment ---")
    audit = validate_paired_alignment(records, proposed=LR_DEFAULT, reference=HGB_DEFAULT)
    print(f"  Alignment Status:       {audit['status']}")
    print(f"  Evaluation Seeds:       {audit['seeds']}")
    print(f"  Aligned Cases per Seed: {audit['aligned_cases_per_seed']}")

    # 4. Compute Full-Study Decision Counts
    units = prediction_units(records)
    seeds = audit["seeds"]
    counts_rows = []

    for m in (LR_DEFAULT, HGB_DEFAULT):
        c_rows = compute_cohort_decision_counts(units, window="final", model=m, seeds=seeds)
        for r in c_rows:
            counts_rows.append({"cohort": "full-study", **r})

    # 5. Compute Full-Study Paired Block-Bootstrap Intervals
    print("\n--- Step 2: Executing Paired Block-Bootstrap Resampling ---")
    interval_rows = []
    for bl in block_lengths:
        res = paired_block_bootstrap_comparison(
            records,
            proposed=LR_DEFAULT,
            reference=HGB_DEFAULT,
            block_length=bl,
            draws=draws,
            seed=b_seed,
            window="final",
        )
        row = {
            "cohort": "full-study",
            "window": res["window"],
            "proposed": res["proposed"],
            "reference": res["reference"],
            "delta_macro_f1": res["delta"],
            "months": res["months"],
            "ci_95_low": res["low"],
            "ci_95_high": res["high"],
            "draws": res["draws"],
            "block_length": res["block_length"],
            "reason": res["reason"],
        }
        interval_rows.append(row)
        print(
            f"  Block Length {bl}: Delta = {res['delta']:+.4f} | "
            f"95% CI: [{res['low']:+.4f}, {res['high']:+.4f}] (Draws: {draws})"
        )

    # 6. Check External Cohorts Reference Data if present
    if args.reference_intervals.exists() and args.reference_counts.exists():
        print("\n--- Step 3: Incorporating Multi-Cohort Reference Records ---")
        ref_int_df = pd.read_csv(args.reference_intervals)
        ref_cnt_df = pd.read_csv(args.reference_counts)

        # Append non-full-study cohorts from reference
        for _, r in ref_int_df.iterrows():
            if r["cohort"] != "full-study":
                interval_rows.append({
                    "cohort": r["cohort"],
                    "window": r["window"],
                    "proposed": r["proposed"],
                    "reference": r["reference"],
                    "delta_macro_f1": r["delta"],
                    "months": int(r["months"]),
                    "ci_95_low": float(r["low"]),
                    "ci_95_high": float(r["high"]),
                    "draws": int(r["draws"]),
                    "block_length": int(r["block_length"]),
                    "reason": r["reason"],
                })

        for _, r in ref_cnt_df.iterrows():
            if r["cohort"] != "full-study":
                # Support both legacy column name (false_event_alarms) and new name
                false_col = (
                    r["false_dissolve_alarms"]
                    if "false_dissolve_alarms" in r.index
                    else r["false_event_alarms"]
                )
                counts_rows.append({
                    "cohort": r["cohort"],
                    "model": r["model"],
                    "seed": int(r["seed"]),
                    "n": int(r["n"]),
                    "macro_f1": float(r["macro_f1"]),
                    "grow_merge_support": int(r["grow_merge_support"]),
                    "grow_merge_hits": int(r["grow_merge_hits"]),
                    "dissolve_support": int(r["dissolve_support"]),
                    "false_dissolve_alarms": int(false_col),
                })

    # 7. Write Output CSVs
    out_intervals_path = args.output_dir / "lr_hgb_cohort_intervals.csv"
    out_counts_path = args.output_dir / "lr_hgb_cohort_counts.csv"

    df_out_int = pd.DataFrame(interval_rows)
    df_out_int.to_csv(out_intervals_path, index=False)
    print(f"\n[Output] Wrote {len(df_out_int)} rows -> {out_intervals_path}")

    df_out_cnt = pd.DataFrame(counts_rows)
    df_out_cnt.to_csv(out_counts_path, index=False)
    print(f"[Output] Wrote {len(df_out_cnt)} rows -> {out_counts_path}")

    # 8. Print Executive Summary Table
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY: CROSS-COHORT PAIRED COMPARISON (LR vs HGB)")
    print("=" * 70)
    summary_display = df_out_int[df_out_int["block_length"] == 2][
        ["cohort", "delta_macro_f1", "ci_95_low", "ci_95_high", "months"]
    ].copy()
    summary_display.columns = ["Cohort", "Delta (LR - HGB)", "95% CI Low", "95% CI High", "Months"]
    print(summary_display.to_string(index=False))
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
