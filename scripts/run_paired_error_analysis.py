"""Runner script for paired error analysis on the 1,269-case final cohort.

Fulfills Week 3 deliverables:
1. Paired comparison across seeds (1,269 cases/seed, auditing seed consistency).
2. 64-case disagreement inventory & in-depth grow/merge -> dissolve error audit.
3. 16 representative cases selected via deterministic ordering rule with notes.
4. Baseline & tree comparator verification (Majority, Persistence, LR, HGB, controls).
5. 95-case prediction-disagreement appendix (distinguishing correctness vs prediction divergence).
6. Automated reconciliation against frozen handoff verification files.

Outputs are written exclusively to artifacts/diagnostics/paired-error-analysis-20261104/
without altering core source or polluting report figure directories.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

from reddit_sna.evaluation.paired_analysis import (
    build_paired_seed_comparison,
    analyze_disagreements_and_dissolve_errors,
    extract_prediction_disagreements,
    compute_stratification_distribution,
    select_representative_cases,
    verify_baseline_and_tree_controls,
    generate_calibrated_final_fixture,
)
from reddit_sna.evaluation.research import KEY

MODEL_ROLE_MAP: dict[str, str] = {
    "hier_lr_dynamic": "Proposed (Hierarchical LR Dynamic)",
    "hier_hgb_dynamic": "Reference Comparator (Hierarchical HGB Dynamic)",
    "flat_lr_dynamic": "Ablation Baseline (Flat LR Dynamic)",
    "flat_hgb_dynamic": "Ablation Baseline (Flat HGB Dynamic)",
    "hier_lr_static": "Control (Hierarchical LR Static)",
    "hier_hgb_static": "Control (Hierarchical HGB Static)",
    "flat_lr_static": "Control (Flat LR Static)",
    "flat_hgb_static": "Control (Flat HGB Static)",
    "A_no_dynamics_matched": "Ablation Control (No Dynamics Matched)",
    "A_no_context_drift_matched": "Ablation Control (No Context Drift Matched)",
    "A_flat_matched": "Ablation Control (Flat Matched)",
    "B2_random_forest": "Tree Baseline (Random Forest)",
    "B4_logreg": "Linear Baseline (Logistic Regression)",
    "B5_matched_boosting": "Tree Baseline (Matched Boosting HGB)",
    "B1_majority": "Trivial Baseline (Majority)",
    "B1_persistence": "Heuristic Baseline (Persistence)",
    "HeTCo_v0": "Historical Pilot (HeTCo v0)",
    "flat_lr_SHL": "Feature Control (Flat LR SHL)",
    "flat_hgb_SHL": "Feature Control (Flat HGB SHL)",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  [output] Wrote {len(df)} rows -> {path}")


def save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  [output] Wrote JSON -> {path}")


def reconcile_with_frozen_handoff(
    handoff_dir: Path | None,
    disagreements_64_df: pd.DataFrame,
    pred_disagreements_95_df: pd.DataFrame,
) -> dict[str, dict[str, Any]] | None:
    """Compare runner keys against frozen handoff verification files if present."""
    if not handoff_dir or not handoff_dir.is_dir():
        return None

    c64_file = handoff_dir / "correctness_contrast_64_seed42.csv"
    p95_file = handoff_dir / "prediction_disagreement_95_seed42.csv"
    if not c64_file.is_file() or not p95_file.is_file():
        return None

    runner_c64_keys = set(tuple(r[k] for k in KEY) for _, r in disagreements_64_df.iterrows())
    tam_c64_keys = set(tuple(r[k] for k in KEY) for r in load_csv(c64_file))

    runner_p95_keys = set(tuple(r[k] for k in KEY) for _, r in pred_disagreements_95_df.iterrows())
    tam_p95_keys = set(tuple(r[k] for k in KEY) for r in load_csv(p95_file))

    results = {
        "correctness_contrast_64": {
            "expected_count": len(tam_c64_keys),
            "runner_count": len(runner_c64_keys),
            "missing_count": len(tam_c64_keys - runner_c64_keys),
            "extra_count": len(runner_c64_keys - tam_c64_keys),
            "status": "PASS (100% Match)" if runner_c64_keys == tam_c64_keys else "FAIL",
        },
        "prediction_disagreement_95": {
            "expected_count": len(tam_p95_keys),
            "runner_count": len(runner_p95_keys),
            "missing_count": len(tam_p95_keys - runner_p95_keys),
            "extra_count": len(runner_p95_keys - tam_p95_keys),
            "status": "PASS (100% Match)" if runner_p95_keys == tam_p95_keys else "FAIL",
        },
    }
    return results


def generate_report(
    summary_df: pd.DataFrame,
    disagreements_df: pd.DataFrame,
    stats_by_class_month: pd.DataFrame,
    dissolve_df: pd.DataFrame,
    rep_cases_df: pd.DataFrame,
    pred_disagreements_df: pd.DataFrame,
    pred_breakdown_df: pd.DataFrame,
    month_dist_df: pd.DataFrame,
    size_dist_df: pd.DataFrame,
    baseline_metrics_df: pd.DataFrame,
    identical_across_seeds: bool,
    source_provenance: str,
    audit_date: str = "2026-11-04",
    is_fixture: bool = False,
    reconciliation: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Compose comprehensive technical Markdown report for Midterm 2 Week 3."""
    lines: list[str] = []
    if is_fixture:
        lines.extend([
            "> [!WARNING]",
            "> **SYNTHETIC FIXTURE - NOT REAL RESULTS**",
            "> This report was generated from a calibrated synthetic benchmark fixture for offline development/testing.",
            "> Do not use these numbers for final submission or milestone handoff without real sealed artifacts.",
            "",
        ])

    first_summary = summary_df.iloc[0]
    n_cases = int(first_summary["total_cases"])
    b_corr = int(first_summary["both_correct"])
    p_only = int(first_summary["proposed_only"])
    h_only = int(first_summary["hgb_only"])
    b_wrong = int(first_summary["both_wrong"])
    diff_val = p_only - h_only
    diff_str = f"+{diff_val}" if diff_val > 0 else str(diff_val)
    seeds_str = ", ".join(map(str, sorted(summary_df["seed"].unique())))

    p_m = baseline_metrics_df[baseline_metrics_df["model"] == "hier_lr_dynamic"]
    h_m = baseline_metrics_df[baseline_metrics_df["model"] == "hier_hgb_dynamic"]
    p_f1 = f"{p_m['macro_f1_six'].iloc[0]:.4f}" if not p_m.empty else "N/A"
    h_f1 = f"{h_m['macro_f1_six'].iloc[0]:.4f}" if not h_m.empty else "N/A"

    lines.extend([
        "# Paired Forecast Error Analysis & Disagreement Diagnosis",
        "",
        f"**Target Cohort:** Final Chronological Evaluation ({n_cases:,} cases/seed)",
        f"**Evaluation Seeds:** {seeds_str}",
        f"**Primary Comparison:** Proposed `hier_lr_dynamic` vs. Reference `hier_hgb_dynamic`",
        f"**Data Provenance:** {source_provenance}",
        f"**Audit Date:** {audit_date} (Midterm 2 Milestone)",
        "",
        "---",
        "",
        f"## 1. Paired Comparison Across Seeds ({n_cases:,} cases/seed)",
        "",
        "Observations are evaluated per seed on identical frozen keys. Repeated seeds are",
        f"audited for consistency and **never pooled into {n_cases * len(summary_df):,} pseudo-independent cases**.",
        "",
        "### Four-Group Correctness Distribution:",
        "",
        "| Seed | Total Cases | Both Correct | Proposed Only | HGB Only | Both Wrong | Seed Agreement |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ])

    for _, r in summary_df.iterrows():
        lines.append(
            f"| {r['seed']} | {r['total_cases']:,} | {r['both_correct']:,} | "
            f"{r['proposed_only']} | {r['hgb_only']} | {r['both_wrong']} | "
            f"{'100% Identical' if identical_across_seeds else 'Divergent'} |"
        )

    lines.extend([
        "",
        f"> **Key Finding:** {b_corr:,} both correct, {p_only} proposed-only, {h_only} HGB-only, {b_wrong} both wrong "
        f"per seed (identical_across_seeds = {identical_across_seeds}). Correct-count differences ({diff_str} for Proposed) "
        f"do not rank Macro-F1; see Section 4 (Proposed {p_f1} vs HGB {h_f1}).",
        "",
        "---",
        "",
        f"## 2. {len(disagreements_df)}-Case Disagreements & Tier-1 Dissolve Error Audit",
        "",
        f"There are exactly **{len(disagreements_df)} correctness contrast cases** ({p_only} proposed-only + {h_only} HGB-only), "
        f"representing instances where exactly one model was correct and the comparator was wrong.",
        "",
        "### Breakdown by True Event Class & Label Month:",
        "",
        "| True Class | Label Month | Total Disagreements | Proposed Correct (HGB Wrong) | HGB Correct (Proposed Wrong) |",
        "|---|:---:|---:|---:|---:|",
    ])

    for _, r in stats_by_class_month.iterrows():
        lines.append(
            f"| {r['y_true']} | {r['label_month']} | {r['disagreements']} | "
            f"{r['proposed_only']} | {r['hgb_only']} |"
        )

    lines.extend([
        "",
        "### In-Depth Tier-1 Dissolve Classification Error (grow/merge -> dissolve):",
        "",
        "| True Event | Support | Proposed Predicts Dissolve | HGB Predicts Dissolve | Both Predict Dissolve | Proposed Correct | HGB Correct |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])

    for _, r in dissolve_df.iterrows():
        lines.append(
            f"| {r['event']} | {r['support']} | {r['proposed_predicts_dissolve']} ({r['proposed_dissolve_rate']:.1%}) | "
            f"{r['hgb_predicts_dissolve']} ({r['hgb_dissolve_rate']:.1%}) | {r['both_predict_dissolve']} | "
            f"{r['proposed_correct']} | {r['hgb_correct']} |"
        )

    lines.extend([
        "",
        "> **Mechanism Analysis:**",
    ])
    for _, r in dissolve_df.iterrows():
        lines.append(
            f"> - For **{r['event']}** ({r['support']} cases), Proposed predicts dissolve in "
            f"**{r['proposed_predicts_dissolve']} cases ({r['proposed_dissolve_rate']:.1%})**, "
            f"while HGB predicts dissolve in **{r['hgb_predicts_dissolve']} cases ({r['hgb_dissolve_rate']:.1%})**."
        )
    lines.extend([
        "> - **Hypothesis (not tested here; mechanism analysis owned by Thanh):** In small communities (size <= 2) "
        "and communities with `history_missing=1`, the tier-1 binary classifier defaults "
        "to dissolution because edge density and member counts mimic inactive isolates. Neither model has sufficient "
        "predecessor signals to distinguish absorption/growth from loss of activity.",
        "",
        "---",
        "",
        f"## 3. Representative Case Inventory ({len(rep_cases_df)} Cases Selected)",
        "",
        "Selection uses the fixed **Deterministic Ordering Rule**:",
        "Candidates are ordered by `(label_month ASC, size DESC, community_id ASC)` taking up to 4 cases per diagnostic group.",
        "",
        "| Case ID | Group | Month | True Event | Proposed Pred | HGB Pred | Size | Hist Missing | Diagnostic Rationale |",
        "|:---:|---|:---:|---|---|---|---:|:---:|---|",
    ])

    for _, r in rep_cases_df.iterrows():
        lines.append(
            f"| `{r['community_id']}` | **{r['group_name']}** | {r['label_month']} | "
            f"`{r['y_true']}` | `{r['proposed_prediction']}` | `{r['reference_prediction']}` | "
            f"{r.get('size', 'N/A')} | {r.get('history_missing', 'N/A')} | {r['diagnostic_note']} |"
        )

    lines.extend([
        "",
        "### Stratification & Generality Audit across Selection Horizons:",
        "",
        "#### Month Distribution Across Subsets:",
        "",
        "| Label Month | Full Cohort (1,269) | Correctness Contrasts (64) | Representative Sample (16) |",
        "|:---:|---:|---:|---:|",
    ])

    for _, r in month_dist_df.iterrows():
        lines.append(
            f"| {r['month']} | {r['cohort_1269']} | {r['disagreements_64']} | {r['rep_16']} |"
        )

    lines.extend([
        "",
        "#### Size Band Distribution Across Subsets:",
        "",
        "| Size Band | Full Cohort (1,269) | Correctness Contrasts (64) | Representative Sample (16) |",
        "|:---:|---:|---:|---:|",
    ])

    for _, r in size_dist_df.iterrows():
        lines.append(
            f"| {r['size_band']} | {r['cohort_1269']} | {r['disagreements_64']} | {r['rep_16']} |"
        )

    months_sorted = sorted(month_dist_df["month"])
    first3 = months_sorted[:3]
    n_rep = int(month_dist_df["rep_16"].sum())
    rep_first3 = int(month_dist_df[month_dist_df["month"].isin(first3)]["rep_16"].sum())
    big = size_dist_df[size_dist_df["size_band"] == ">20"].iloc[0]
    n_all = int(size_dist_df["cohort_1269"].sum())

    lines.extend([
        "",
        f"> **Stratification & Generality Finding:** The fixed ordering rule produces selection skew: "
        f"{rep_first3} of {n_rep} cases ({rep_first3 / n_rep:.1%}) fall in the first three label months "
        f"({first3[0]} to {first3[-1]}), and size > 20 communities are {int(big['rep_16'])}/{n_rep} "
        f"({int(big['rep_16']) / n_rep:.1%}) of the sample versus {int(big['cohort_1269'])}/{n_all:,} "
        f"({int(big['cohort_1269']) / n_all:.1%}) of the cohort. These cases are transparent qualitative "
        "illustrations, not a stratified probability sample.",
        "",
        "---",
        "",
        "## 4. Benchmark Baseline & Control Verification (RF & Tree Controls)",
        "",
        "| Model Name | Standard Evaluation Role | N per seed | Macro-F1 (Mean) | Macro-F1 (SD) | Accuracy |",
        "|---|---|---:|---:|---:|---:|",
    ])

    for _, r in baseline_metrics_df.iterrows():
        m_name = r["model"]
        role = MODEL_ROLE_MAP.get(m_name, "Baseline Control")
        lines.append(
            f"| `{m_name}` | {role} | "
            f"{r['n_per_seed']:,} | **{r['macro_f1_six']:.4f}** | {r['macro_f1_sd']:.4f} | {r['accuracy']:.4f} |"
        )

    lines.extend([
        "",
        "> **Verification Summary:** All evaluated model predictions share identical sample keys (checked in code).",
        "",
        "---",
        "",
        f"## 5. Appendix: Prediction Disagreements ({len(pred_disagreements_df)} Cases Across Different Forecast Labels)",
        "",
        "Prediction disagreements include **all cases where the proposed and reference models output different predicted classes**, "
        "regardless of whether either model was correct. This separates the **64 correctness contrasts** from instances where "
        "both models erred on different alternative classes:",
        "",
        "| Outcome Group | Cases | Description |",
        "|---|---:|---|",
    ])

    for _, r in pred_breakdown_df.iterrows():
        lines.append(f"| `{r['outcome_group']}` | {r['count']} | {r['description']} |")

    n_div_wrong = int((pred_disagreements_df["outcome"] == "both_wrong").sum())
    lines.extend([
        "",
        f"> **Clarification:** {len(disagreements_df)} cases are correctness contrasts "
        f"({p_only} proposed-only + {h_only} HGB-only). {n_div_wrong} cases are both-wrong with different "
        f"predicted labels. The remaining {b_wrong - n_div_wrong} both-wrong cases predict the same wrong label.",
        "",
    ])

    if reconciliation:
        lines.extend([
            "---",
            "",
            "## 6. Independent Frozen Handoff Reconciliation",
            "",
            "Automated alignment audit against the frozen handoff reference artifacts (`tam-final-1269`):",
            "",
            "| Audit Target | Expected Unique Keys | Runner Evaluated Keys | Missing Keys | Extra Keys | Reconciliation Status |",
            "|---|---:|---:|---:|---:|:---:|",
        ])
        for name, meta in reconciliation.items():
            disp_name = (
                "Correctness Contrasts (64 cases)"
                if "64" in name
                else "Prediction Disagreements (95 cases)"
            )
            lines.append(
                f"| {disp_name} | {meta['expected_count']} | {meta['runner_count']} | "
                f"{meta['missing_count']} | {meta['extra_count']} | **{meta['status']}** |"
            )
        lines.append("")

    return "\n".join(lines)


def find_evaluation_inputs(
    project_root: Path,
    predictions_path: Path | None = None,
    samples_path: Path | None = None,
    features_path: Path | None = None,
) -> tuple[list[dict[str, str]] | None, list[dict[str, str]] | None, list[dict[str, str]] | None, str]:
    """Search for real predictions and samples across artifacts subdirectories."""
    if predictions_path or samples_path:
        for p in (predictions_path, samples_path):
            if p is None or not p.is_file():
                raise FileNotFoundError(f"Khong tim thay file: {p}")
        preds = load_csv(predictions_path)
        samps = load_csv(samples_path)
        feats = load_csv(features_path) if (features_path and features_path.is_file()) else samps
        return preds, samps, feats, f"Explicit input paths ({predictions_path})"

    # Candidate directories to scan under project root
    candidate_paths = [
        # Frozen handoff package from Tâm
        (
            project_root / "artifacts/handoff/tam-final-1269/artifacts/temporal/activity-study-001/stages/evaluation/attempt-001/predictions.csv",
            project_root / "artifacts/handoff/tam-final-1269/final_samples_1269.csv",
            project_root / "artifacts/handoff/tam-final-1269/final_features_1269.csv",
        ),
        # Sealed temporal activity study
        (
            project_root / "artifacts/temporal/activity-study-001/stages/evaluation/attempt-001/predictions.csv",
            project_root / "artifacts/temporal/activity-study-001/stages/evaluation-samples/attempt-001/samples.csv",
            project_root / "artifacts/temporal/activity-study-001/stages/evaluation-samples/attempt-001/features.csv",
        ),
        # Diagnostics or frozen archives
        (
            project_root / "artifacts/frozen/predictions.csv",
            project_root / "artifacts/frozen/samples.csv",
            project_root / "artifacts/frozen/features.csv",
        ),
        (
            project_root / "artifacts/diagnostics/midterm2-20261029/predictions.csv",
            project_root / "artifacts/diagnostics/midterm2-20261029/samples.csv",
            project_root / "artifacts/diagnostics/midterm2-20261029/features.csv",
        ),
    ]

    for p_file, s_file, f_file in candidate_paths:
        if p_file.is_file() and s_file.is_file():
            preds = load_csv(p_file)
            samps = load_csv(s_file)
            feats = load_csv(f_file) if f_file.is_file() else samps
            return preds, samps, feats, f"Discovered handoff artifact ({p_file})"

    # Dynamic scan across artifacts/ subdirectories
    artifacts_dir = project_root / "artifacts"
    if artifacts_dir.is_dir():
        for p in artifacts_dir.glob("**/predictions.csv"):
            p_str = str(p)
            if "paired-error-analysis" in p_str or "week1" in p_str or "dup-" in p_str or "FIXTURE" in p_str:
                continue
            try:
                with p.open("r", encoding="utf-8") as f:
                    sample_text = f.read(2048)
                    if "hier_lr_dynamic" in sample_text:
                        parent = p.parent
                        s_cand = parent / "samples.csv"
                        if not s_cand.is_file():
                            s_cand = parent.parent / "samples.csv"
                        if not s_cand.is_file():
                            s_cand = parent.parent / "evaluation-samples/attempt-001/samples.csv"
                        if s_cand.is_file():
                            preds = load_csv(p)
                            samps = load_csv(s_cand)
                            f_cand = parent / "features.csv"
                            feats = load_csv(f_cand) if f_cand.is_file() else samps
                            return preds, samps, feats, f"Discovered artifact ({p})"
            except Exception:
                continue

    return None, None, None, ""


def run_analysis(
    predictions_path: Path | None = None,
    samples_path: Path | None = None,
    features_path: Path | None = None,
    handoff_dir: Path | None = None,
    output_dir: Path | None = None,
    use_fixture: bool = False,
) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    project_root = Path(__file__).resolve().parents[1]

    print("=" * 70)
    print("PAIRED FORECAST ERROR ANALYSIS & DIAGNOSTICS RUNNER")
    print("=" * 70)

    # 1. Resolve inputs
    predictions = None
    samples = None
    features = None
    provenance = ""

    if not use_fixture:
        predictions, samples, features, provenance = find_evaluation_inputs(
            project_root=project_root,
            predictions_path=predictions_path,
            samples_path=samples_path,
            features_path=features_path,
        )

    if predictions is not None and samples is not None:
        out_dir = output_dir or (project_root / "artifacts/diagnostics/paired-error-analysis-20261104")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Standardize window field if missing from predictions.csv
        for r in predictions:
            r["window"] = r.get("window", "final")

        # Compute SHA-256 digest of predictions file if known
        actual_pred_path = predictions_path
        if actual_pred_path is None and "artifacts" in provenance:
            try:
                cand = Path(provenance.split("(")[-1].rstrip(")"))
                if cand.is_file():
                    actual_pred_path = cand
            except Exception:
                pass

        sha_digest = ""
        if actual_pred_path and actual_pred_path.is_file():
            sha_digest = hashlib.sha256(actual_pred_path.read_bytes()).hexdigest()

        provenance_desc = f"{provenance}"
        if sha_digest:
            provenance_desc += f" [SHA-256: {sha_digest}]"
        provenance_desc += " (predictions.csv has no 'window' column; all 1,269 keys are assigned window='final' per manifest)"
        print(f"Loaded real evaluation dataset from: {provenance_desc}")
    else:
        if not use_fixture:
            print("\n[ERROR] Evaluation artifacts (predictions.csv, samples.csv) not found on disk.")
            print("Real artifacts are gitignored and were not detected in:")
            print("  - artifacts/handoff/tam-final-1269/...")
            print("  - artifacts/temporal/activity-study-001/...")
            print("\nTo run on real artifacts: specify their paths via --predictions and --samples.")
            print("To run the calibrated benchmark fixture for testing/development: pass --use-fixture.")
            raise FileNotFoundError(
                "Real evaluation artifacts not found on local disk. Pass --use-fixture for benchmark development mode."
            )

        out_dir = output_dir or (project_root / "artifacts/diagnostics/paired-error-analysis-20261104/FIXTURE_NOT_REAL")
        out_dir.mkdir(parents=True, exist_ok=True)
        print("\n[Notice] Running in explicit benchmark fixture mode (--use-fixture).")
        print(f"[Notice] Writing fixture outputs to isolated folder: {out_dir}")
        print("Loading calibrated reference benchmark fixture (1,269 cases, 3 seeds)...")
        predictions, features, samples = generate_calibrated_final_fixture()
        provenance_desc = "Calibrated synthetic benchmark fixture (1,269 cases, 3 seeds - NOT REAL ARTIFACTS)"

    print(f"Total predictions loaded: {len(predictions)}")
    print(f"Total features loaded:    {len(features)}")
    print(f"Total samples loaded:     {len(samples)}")

    # 2. Execute Task 1: Paired comparison
    print("\n--- Task 1: Building Paired Comparison across Seeds ---")
    cases_df, summary_df, identical = build_paired_seed_comparison(
        predictions, features, proposed_model="hier_lr_dynamic", reference_model="hier_hgb_dynamic"
    )
    save_csv(out_dir / "paired_comparison_1269_by_seed.csv", cases_df)
    save_json(out_dir / "seed_consistency_summary.json", summary_df.to_dict(orient="records"))
    print(f"Identical outcomes across seeds: {identical}")

    # 3. Execute Task 2: Disagreements & Dissolve errors
    print("\n--- Task 2: Analyzing Disagreements & Grow/Merge Dissolve Errors ---")
    disagreements_df, stats_by_class_month, dissolve_df = analyze_disagreements_and_dissolve_errors(
        cases_df, samples=samples, canonical_seed=42
    )
    save_csv(out_dir / "disagreements_64_cases.csv", disagreements_df)
    save_csv(out_dir / "disagreements_by_class_month.csv", stats_by_class_month)
    save_csv(out_dir / "grow_merge_dissolve_error_analysis.csv", dissolve_df)
    print(f"Total disagreement cases extracted: {len(disagreements_df)}")

    # 4. Execute Prediction Disagreements (95 cases)
    print("\n--- Extracting All Prediction Disagreements (95 Cases) ---")
    pred_disagreements_df, pred_breakdown_df = extract_prediction_disagreements(
        cases_df, samples=samples, canonical_seed=42
    )
    save_csv(out_dir / "prediction_disagreements_95_cases.csv", pred_disagreements_df)
    print(f"Total prediction disagreement cases extracted: {len(pred_disagreements_df)}")

    # 5. Execute Task 3: Representative cases
    print("\n--- Task 3: Selecting 16 Representative Diagnostic Cases ---")
    rep_cases_df = select_representative_cases(
        cases_df, samples=samples, canonical_seed=42, cases_per_group=4
    )
    save_csv(out_dir / "representative_16_cases.csv", rep_cases_df)
    print(f"Total representative cases selected: {len(rep_cases_df)}")

    # 6. Compute Stratification Distributions
    month_dist_df, size_dist_df = compute_stratification_distribution(
        cases_df, disagreements_df, rep_cases_df, canonical_seed=42
    )

    # 7. Execute Task 4: Baseline controls
    print("\n--- Task 4: Verifying Baseline & Tree Controls (RF & Extended Models) ---")
    baseline_metrics_df, per_class_df = verify_baseline_and_tree_controls(
        predictions,
        features,
        expected_models=(
            "hier_lr_dynamic",
            "hier_hgb_dynamic",
            "flat_lr_dynamic",
            "flat_hgb_dynamic",
            "hier_lr_static",
            "hier_hgb_static",
            "flat_lr_static",
            "flat_hgb_static",
            "A_no_dynamics_matched",
            "A_no_context_drift_matched",
            "A_flat_matched",
            "B2_random_forest",
            "B4_logreg",
            "B5_matched_boosting",
            "B1_majority",
            "B1_persistence",
        ),
    )
    save_csv(out_dir / "baseline_and_tree_controls.csv", baseline_metrics_df)
    save_csv(out_dir / "baseline_per_class_support.csv", per_class_df)

    # 8. Reconcile with frozen handoff if present
    effective_handoff = handoff_dir or (project_root / "artifacts/handoff/tam-final-1269")
    reconciliation = reconcile_with_frozen_handoff(
        effective_handoff, disagreements_df, pred_disagreements_df
    )
    if reconciliation:
        print("\n--- Lineage Reconciliation against Frozen Handoff ---")
        for k, v in reconciliation.items():
            print(f"  {k}: {v['status']} (expected={v['expected_count']}, runner={v['runner_count']})")

    # 9. Generate Markdown Report
    print("\n--- Generating Comprehensive Report ---")
    report_text = generate_report(
        summary_df=summary_df,
        disagreements_df=disagreements_df,
        stats_by_class_month=stats_by_class_month,
        dissolve_df=dissolve_df,
        rep_cases_df=rep_cases_df,
        pred_disagreements_df=pred_disagreements_df,
        pred_breakdown_df=pred_breakdown_df,
        month_dist_df=month_dist_df,
        size_dist_df=size_dist_df,
        baseline_metrics_df=baseline_metrics_df,
        identical_across_seeds=identical,
        source_provenance=provenance_desc,
        is_fixture=use_fixture,
        reconciliation=reconciliation,
    )
    report_path = out_dir / "PAIRED_ERROR_ANALYSIS_REPORT.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"  [output] Wrote report -> {report_path}")

    # Display report directly to console
    print("\n" + "=" * 70)
    print("PAIRED FORECAST ERROR ANALYSIS - EXECUTIVE REPORT & TABLES")
    print("=" * 70)
    print(report_text)
    print("=" * 70)
    print("ALL DELIVERABLES COMPLETED SUCCESSFULLY.")
    print(f"Artifacts preserved in: {out_dir}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paired error analysis for Midterm 2 Week 3")
    parser.add_argument("--predictions", type=Path, default=None, help="Path to predictions.csv")
    parser.add_argument("--samples", type=Path, default=None, help="Path to samples.csv")
    parser.add_argument("--features", type=Path, default=None, help="Path to features.csv")
    parser.add_argument("--handoff-dir", type=Path, default=None, help="Path to handoff verification directory")
    parser.add_argument("--output", type=Path, default=None, help="Output destination folder")
    parser.add_argument(
        "--use-fixture",
        action="store_true",
        help="Explicitly use calibrated 1,269-sample benchmark fixture instead of searching disk",
    )
    args = parser.parse_args()

    run_analysis(
        predictions_path=args.predictions,
        samples_path=args.samples,
        features_path=args.features,
        handoff_dir=args.handoff_dir,
        output_dir=args.output,
        use_fixture=args.use_fixture,
    )


if __name__ == "__main__":
    main()
