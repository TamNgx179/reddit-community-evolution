import argparse
import json
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================



MODEL = "B2_random_forest"
SEEDS = [42, 43, 44]

SAMPLE_KEY = [
    "reference_id",
    "feature_month",
    "community_id",
    "label_month",
    "label_reference_id",
]

REQUIRED = SAMPLE_KEY + [
    "model",
    "seed",
    "y_true",
    "y_pred",
    "window",
]


# ============================================================
# LOAD AND VALIDATE
# ============================================================

def main():
    global INPUT, OUT

    parser = argparse.ArgumentParser(
        description="Analyze prediction agreement across B2 seeds."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to predictions_final.csv.",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory. Existing directories are not overwritten.",
    )

    args = parser.parse_args()

    INPUT = args.input.expanduser().resolve()
    OUT = args.out.expanduser().resolve()

    if not INPUT.is_file():
        raise FileNotFoundError(
            f"Prediction input not found: {INPUT}"
        )

    if OUT.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUT}"
        )

    OUT.mkdir(parents=True)

    print("[1/5] Reading B2 predictions...")

    df = pd.read_csv(
        INPUT,
        usecols=REQUIRED,
        dtype={
            "seed": "int64",
            "community_id": "string",
        },
    )

    df = df[
        (df["window"] == "final")
        & (df["model"] == MODEL)
        & (df["seed"].isin(SEEDS))
    ].copy()

    print("[2/5] Validating sample keys...")

    if df.duplicated(SAMPLE_KEY + ["seed"]).any():
        raise ValueError("Duplicate sample/seed prediction rows.")

    counts = df.groupby("seed").size().to_dict()

    if counts != {42: 1269, 43: 1269, 44: 1269}:
        raise ValueError(f"Unexpected seed row counts: {counts}")

    if df[SAMPLE_KEY].drop_duplicates().shape[0] != 1269:
        raise ValueError("Unexpected number of unique samples.")

    # Every sample must have the same true label across seeds.
    true_label_counts = (
        df.groupby(SAMPLE_KEY)["y_true"].nunique()
    )

    if (true_label_counts != 1).any():
        raise ValueError("Inconsistent y_true across seeds.")

    # Every sample must have all three seeds.
    seed_counts = df.groupby(SAMPLE_KEY)["seed"].nunique()

    if (seed_counts != 3).any():
        raise ValueError("Some samples are missing a seed.")

    print("[3/5] Comparing predictions across seeds...")

    pred = df.pivot(
        index=SAMPLE_KEY,
        columns="seed",
        values="y_pred",
    ).reset_index()

    truth = (
        df.groupby(SAMPLE_KEY, as_index=False)["y_true"]
        .first()
    )

    pred = pred.merge(
        truth,
        on=SAMPLE_KEY,
        how="left",
        validate="one_to_one",
    )

    pred["all_three_agree"] = (
        (pred[42] == pred[43])
        & (pred[42] == pred[44])
    )

    pred["any_seed_differs"] = ~pred["all_three_agree"]

    pred["distinct_predictions"] = pred[
        SEEDS
    ].nunique(axis=1)

    # Pairwise agreement.
    pred["agree_42_43"] = pred[42] == pred[43]
    pred["agree_42_44"] = pred[42] == pred[44]
    pred["agree_43_44"] = pred[43] == pred[44]

    # Save sample-level records for audit.
    pred.to_csv(
        OUT / "B2_sample_seed_agreement.csv",
        index=False,
    )

    print("[4/5] Building summary tables...")

    n = len(pred)

    summary = pd.DataFrame([
        {
            "model": MODEL,
            "samples": n,
            "all_three_agree": int(
                pred["all_three_agree"].sum()
            ),
            "all_three_agree_pct": (
                pred["all_three_agree"].mean() * 100
            ),
            "at_least_one_differs": int(
                pred["any_seed_differs"].sum()
            ),
            "at_least_one_differs_pct": (
                pred["any_seed_differs"].mean() * 100
            ),
            "agreement_42_43": (
                pred["agree_42_43"].mean()
            ),
            "agreement_42_44": (
                pred["agree_42_44"].mean()
            ),
            "agreement_43_44": (
                pred["agree_43_44"].mean()
            ),
        }
    ])

    summary.to_csv(
        OUT / "B2_seed_agreement_summary.csv",
        index=False,
    )

    # Agreement and disagreement by true class.
    class_rows = []

    for label, group in pred.groupby("y_true"):
        class_rows.append({
            "y_true": label,
            "support": len(group),
            "all_three_agree": int(
                group["all_three_agree"].sum()
            ),
            "all_three_agree_pct": (
                group["all_three_agree"].mean() * 100
            ),
            "at_least_one_differs": int(
                group["any_seed_differs"].sum()
            ),
            "agreement_42_43": (
                group["agree_42_43"].mean()
            ),
            "agreement_42_44": (
                group["agree_42_44"].mean()
            ),
            "agreement_43_44": (
                group["agree_43_44"].mean()
            ),
        })

    class_summary = pd.DataFrame(class_rows)

    class_summary.to_csv(
        OUT / "B2_agreement_by_true_class.csv",
        index=False,
    )

    # Prediction pattern counts.
    pattern = (
        pred.groupby(
            ["y_true", 42, 43, 44],
            dropna=False,
        )
        .size()
        .reset_index(name="support")
        .rename(columns={
            42: "prediction_seed_42",
            43: "prediction_seed_43",
            44: "prediction_seed_44",
        })
        .sort_values(
            ["y_true", "support"],
            ascending=[True, False],
        )
    )

    pattern.to_csv(
        OUT / "B2_prediction_patterns.csv",
        index=False,
    )

    print("[5/5] Saving audit...")

    audit = {
        "model": MODEL,
        "seeds": SEEDS,
        "prediction_rows": int(len(df)),
        "unique_samples": int(n),
        "rows_per_seed": counts,
        "all_samples_have_three_seeds": True,
        "y_true_consistent_across_seeds": True,
        "duplicate_sample_seed_rows": 0,
        "all_three_agree": int(
            pred["all_three_agree"].sum()
        ),
        "at_least_one_differs": int(
            pred["any_seed_differs"].sum()
        ),
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

    print("\nDONE")
    print("Output:", OUT)
    print("Samples:", n)
    print("All three agree:", audit["all_three_agree"])
    print("At least one differs:", audit["at_least_one_differs"])
    print("Agreement summary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()