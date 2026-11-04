import argparse
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

SOURCE = None
OUT = None

EXPECTED_SEEDS = {42, 43, 44}

MACRO_TABLES = {
    "A1_overall": "A1_overall_macro_summary.csv",
    "A1_monthly": "A1_monthly_macro_summary.csv",
    "A2_size": "A2_size_macro_summary.csv",
    "A2_lineage_history": "A2_lineage_history_macro_summary.csv",
    "A2_member_activity_history": (
        "A2_member_activity_history_macro_summary.csv"
    ),
    "A2_size_history": "A2_size_history_macro_summary.csv",
    "A2_stratified": "A2_stratified_macro_summary.csv",
}

CLASS_TABLES = {
    "A1_overall": "A1_overall_class_metrics.csv",
    "A1_monthly": "A1_monthly_class_metrics.csv",
    "A2_size": "A2_size_class_metrics.csv",
    "A2_lineage_history": "A2_lineage_history_class_metrics.csv",
    "A2_member_activity_history": (
        "A2_member_activity_history_class_metrics.csv"
    ),
    "A2_size_history": "A2_size_history_class_metrics.csv",
    "A2_stratified": "A2_stratified_class_metrics.csv",
}

CLASS_ORDER = [
    "stable", "grow", "shrink",
    "merge", "split", "dissolve",
]

SIZE_ORDER = ["2", "3-4", "5-20", ">20"]


# ============================================================
# 2. VALIDATION HELPERS
# ============================================================

def read_source(filename):
    path = SOURCE / filename

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)

    required = {"model", "seed"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{filename}: missing columns {sorted(missing)}"
        )

    df["seed"] = pd.to_numeric(
        df["seed"], errors="raise"
    ).astype(int)

    unexpected = set(df["seed"].unique()) - EXPECTED_SEEDS

    if unexpected:
        raise ValueError(
            f"{filename}: unexpected seeds {unexpected}"
        )

    return df


def aggregate_table(
    df,
    metric_columns,
    invariant_columns,
    table_name,
):
    """
    Aggregate metrics across seeds.

    - Metric columns: mean and sample SD (ddof=1).
    - Invariant columns: must be identical across seeds.
    - Each group must contain exactly seeds 42, 43, 44.
    """

    excluded = (
        {"seed"}
        | set(metric_columns)
        | set(invariant_columns)
    )

    group_columns = [
        col for col in df.columns
        if col not in excluded
    ]

    if not group_columns:
        raise ValueError(
            f"{table_name}: no grouping columns found."
        )

    if df.duplicated(group_columns + ["seed"]).any():
        raise ValueError(
            f"{table_name}: duplicate group/seed rows."
        )

    results = []

    grouped = df.groupby(
        group_columns,
        dropna=False,
        sort=True,
    )

    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)

        seed_set = set(group["seed"].tolist())

        if seed_set != EXPECTED_SEEDS or len(group) != 3:
            raise ValueError(
                f"{table_name}: invalid seed group "
                f"{dict(zip(group_columns, key))}; "
                f"found {sorted(seed_set)}"
            )

        row = dict(zip(group_columns, key))
        row["seed_count"] = len(group)

        for column in invariant_columns:
            if column not in df.columns:
                continue

            values = group[column].drop_duplicates()

            if len(values) != 1:
                raise ValueError(
                    f"{table_name}: {column} differs across "
                    f"seeds in group {row}"
                )

            row[column] = values.iloc[0]

        for metric in metric_columns:
            values = pd.to_numeric(
                group[metric],
                errors="raise",
            )

            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_sd"] = values.std(ddof=1)

        results.append(row)

    result = pd.DataFrame(results)

    if result.empty:
        raise ValueError(f"{table_name}: empty aggregate.")

    return result


# ============================================================
# 3. AGGREGATE MACRO METRICS
# ============================================================

def aggregate_macro_tables():
    outputs = {}
    audit = {}

    for name, filename in MACRO_TABLES.items():
        print(f"[MACRO] {filename}")

        df = read_source(filename)

        metrics = [
            col for col in ["macro_f1_six", "accuracy"]
            if col in df.columns
        ]

        invariant = [
            col for col in ["n"]
            if col in df.columns
        ]

        result = aggregate_table(
            df,
            metric_columns=metrics,
            invariant_columns=invariant,
            table_name=name,
        )

        result.to_csv(
            OUT / f"{name}_mean_sd.csv",
            index=False,
        )

        outputs[name] = result

        audit[name] = {
            "source_rows": int(len(df)),
            "aggregate_rows": int(len(result)),
            "models": int(df["model"].nunique()),
            "metric_columns": metrics,
            "invariant_columns": invariant,
        }

    return outputs, audit


# ============================================================
# 4. AGGREGATE PER-CLASS METRICS
# ============================================================

def aggregate_class_tables():
    outputs = {}
    audit = {}

    for name, filename in CLASS_TABLES.items():
        print(f"[CLASS] {filename}")

        df = read_source(filename)

        metrics = [
    		col for col in [
        		"precision",
        		"recall",
        		"f1",
        		"to_dissolve",
        		"predicted",
    		]
    		if col in df.columns
	]

        invariant = [
            col for col in ["support"]
            if col in df.columns
        ]

        result = aggregate_table(
            df,
            metric_columns=metrics,
            invariant_columns=invariant,
            table_name=name,
        )

        result.to_csv(
            OUT / f"{name}_class_mean_sd.csv",
            index=False,
        )

        outputs[name] = result

        audit[name] = {
            "source_rows": int(len(df)),
            "aggregate_rows": int(len(result)),
            "models": int(df["model"].nunique()),
            "metric_columns": metrics,
            "invariant_columns": invariant,
        }

    return outputs, audit


# ============================================================
# 5. PLOTTING HELPERS
# ============================================================

def heatmap(
    df,
    value_column,
    index_column,
    column_column,
    title,
    output_name,
    column_order=None,
):
    if df.empty:
        return

    pivot = df.pivot(
        index=index_column,
        columns=column_column,
        values=value_column,
    )

    if column_order:
        ordered = [
            item for item in column_order
            if item in pivot.columns
        ]
        remaining = [
            item for item in pivot.columns
            if item not in ordered
        ]
        pivot = pivot.reindex(
            columns=ordered + remaining
        )

    pivot = pivot.sort_index()

    height = max(5, 0.34 * len(pivot.index))
    width = max(7, 0.9 * len(pivot.columns))

    fig, ax = plt.subplots(
        figsize=(width, height)
    )

    image = ax.imshow(
        pivot.to_numpy(dtype=float),
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(
        [str(x) for x in pivot.columns],
        rotation=35,
        ha="right",
    )

    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(
        [str(x) for x in pivot.index],
        fontsize=8,
    )

    ax.set_title(title)
    ax.set_xlabel(column_column)
    ax.set_ylabel("Model")

    fig.colorbar(
        image,
        ax=ax,
        label=value_column,
    )

    fig.tight_layout()
    fig.savefig(
        OUT / output_name,
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_overall_ranking(df):
    if df.empty:
        return

    plot_df = df.sort_values(
        "macro_f1_six_mean",
        ascending=True,
    ).copy()

    fig_height = max(7, 0.38 * len(plot_df))

    fig, ax = plt.subplots(
        figsize=(11, fig_height)
    )

    ax.barh(
        plot_df["model"],
        plot_df["macro_f1_six_mean"],
        xerr=plot_df["macro_f1_six_sd"],
        capsize=3,
    )

    ax.set_xlabel("Six-class Macro-F1 (mean ± sample SD)")
    ax.set_ylabel("Model")
    ax.set_title(
        "A1 — Overall Final-Window Macro-F1"
    )

    ax.grid(
        axis="x",
        alpha=0.25,
    )

    fig.tight_layout()
    fig.savefig(
        OUT / "FIG_A1_overall_macro_f1.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)


# ============================================================
# 6. GENERATE FIGURES
# ============================================================

def generate_figures(macro, classes):
    print("[PLOT] Generating figures...")

    # A1 overall model comparison.
    plot_overall_ranking(macro["A1_overall"])

    # A1 monthly performance.
    heatmap(
        macro["A1_monthly"],
        "macro_f1_six_mean",
        "model",
        "stratum",
        "A1 — Monthly Macro-F1 Mean",
        "FIG_A1_monthly_macro_f1.png",
    )

    # A1 per-class F1.
    heatmap(
        classes["A1_overall"],
        "f1_mean",
        "model",
        "label",
        "A1 — Overall Per-Class F1 Mean",
        "FIG_A1_class_f1.png",
        CLASS_ORDER,
    )

    # A2 size.
    heatmap(
        macro["A2_size"],
        "macro_f1_six_mean",
        "model",
        "stratum",
        "A2 — Macro-F1 by Community Size",
        "FIG_A2_size_macro_f1.png",
        SIZE_ORDER,
    )

    # A2 lineage history.
    heatmap(
        macro["A2_lineage_history"],
        "macro_f1_six_mean",
        "model",
        "stratum",
        "A2 — Macro-F1 by Lineage History",
        "FIG_A2_lineage_history.png",
    )

    # A2 member activity history.
    heatmap(
        macro["A2_member_activity_history"],
        "macro_f1_six_mean",
        "model",
        "stratum",
        "A2 — Macro-F1 by Member Activity History",
        "FIG_A2_member_activity_history.png",
    )

    # A2 joint size and lineage history.
    heatmap(
        macro["A2_size_history"],
        "macro_f1_six_mean",
        "model",
        "stratum",
        "A2 — Macro-F1 by Size × Lineage History",
        "FIG_A2_size_history.png",
    )


# ============================================================
# 7. WRITE README AND AUDIT
# ============================================================

def write_documentation(macro_audit, class_audit):
    audit = {
        "source_directory": str(SOURCE),
        "output_directory": str(OUT),
        "expected_seeds": sorted(EXPECTED_SEEDS),
        "aggregation": {
            "mean": "Arithmetic mean across seeds",
            "sd": "Sample standard deviation (ddof=1)",
            "support": (
                "Invariant support retained once; "
                "not multiplied by three."
            ),
            "n": (
                "Invariant sample count retained once; "
                "not multiplied by three."
            ),
        },
        "macro_tables": macro_audit,
        "class_tables": class_audit,
        "notes": [
            "Final-window predictions only.",
            "No model was fitted or refitted.",
            "No predictions were regenerated.",
            "Each model/stratum was aggregated across seeds 42, 43, 44.",
            "Seeds are repeated runs, not independent communities.",
            "Confusion matrices remain in the original per-seed exports.",
            "Support is not summed across seeds.",
            "Macro-F1 uses the fixed six-class convention.",
        ],
    }

    with open(
        OUT / "validation_audit.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            audit,
            f,
            indent=2,
            ensure_ascii=False,
        )

    readme = """A1 + A2 — AGGREGATED FINAL-WINDOW RESULTS

Source:
- analysis_outputs_20261104_A1_A2_run2/

Aggregation:
- Three seeds: 42, 43, 44.
- Arithmetic mean across seeds.
- Sample standard deviation (ddof=1).
- Support and n are retained once after checking equality.
- Support is not multiplied by three.
- No model is fitted or refitted.

A1:
- Overall Macro-F1 and accuracy.
- Monthly Macro-F1 and accuracy.
- Per-class precision, recall and F1.
- Overall per-class F1 visualization.

A2:
- Community size.
- Lineage history.
- Member activity history.
- Joint size × lineage-history strata.
- Stratified combined tables.

Figures:
- Overall model ranking with sample SD error bars.
- Monthly Macro-F1 heatmap.
- Overall per-class F1 heatmap.
- Size and history Macro-F1 heatmaps.

Important:
- Results use final-window predictions only.
- Final sample count is 1,269.
- Unresolved and censored targets are not predictive labels.
- Seeds are repeat runs, not independent samples.
- Original per-seed confusion matrices remain unchanged.
- SD=0 means identical metric values across these three seeds;
  it does not establish general model certainty.
"""

    (OUT / "README_A1_A2_AGGREGATED.txt").write_text(
        readme,
        encoding="utf-8",
    )


# ============================================================
# 8. MAIN
# ============================================================

def main():
    global SOURCE, OUT

    parser = argparse.ArgumentParser(
        description="Aggregate A1/A2 metrics across seeds."
    )

    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Directory containing per-seed A1/A2 CSV files.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory. Existing directories are not overwritten.",
    )

    args = parser.parse_args()

    SOURCE = args.source.expanduser().resolve()
    OUT = args.out.expanduser().resolve()

    if not SOURCE.is_dir():
        raise FileNotFoundError(
            f"Source directory not found: {SOURCE}"
        )

    if OUT.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUT}"
        )

    OUT.mkdir(parents=True)

    print("[1/5] Aggregating macro metrics...")
    macro, macro_audit = aggregate_macro_tables()

    print("[2/5] Aggregating per-class metrics...")
    classes, class_audit = aggregate_class_tables()

    print("[3/5] Generating figures...")
    generate_figures(macro, classes)

    print("[4/5] Writing audit and README...")
    write_documentation(
        macro_audit,
        class_audit,
    )

    print("[5/5] Checking output files...")

    files = sorted(
        p.name for p in OUT.iterdir()
        if p.is_file()
    )

    if not files:
        raise RuntimeError("No output files generated.")

    print("\nDONE")
    print("Source:", SOURCE)
    print("Output:", OUT)
    print("Macro aggregate tables:", len(macro))
    print("Class aggregate tables:", len(classes))
    print("Total output files:", len(files))

    for filename in files:
        print(" -", filename)


if __name__ == "__main__":
    main()