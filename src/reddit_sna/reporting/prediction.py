"""Verified presentation of the synthetic table baseline results."""

from hashlib import sha256
import json
from pathlib import Path


def read_prediction(run):
    """Verify hashes and recompute saved metrics before rendering them."""
    import pandas as pd
    from reddit_sna.evaluation.metrics import evaluate_predictions, confusion_matrices

    root = Path(run).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete_through_baselines" or manifest["stage_status"].get("evaluation") != "complete":
        raise ValueError("A completed prediction evaluation is required")
    for name, digest in manifest["artifact_hashes"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Prediction artifact path/hash mismatch")
    predictions = pd.read_csv(root / "predictions.csv")
    split = pd.read_csv(root / "split.csv")
    if set(predictions["model"]) != {"B1_majority", "B1_persistence", "B4_logreg"}:
        raise ValueError("Missing declared baseline model in predictions")
    keys = ["reference_id", "feature_month", "community_id", "label_month"]
    expected_keys = set(map(tuple, split[keys].to_numpy()))
    for model, rows in predictions.groupby("model"):
        if set(map(tuple, rows[keys].to_numpy())) != expected_keys:
            raise ValueError(f"Incomplete prediction population for {model}")
    recomputed = evaluate_predictions(predictions, split)
    for name, expected in recomputed.items():
        filename = "per_class.csv" if name == "per_class" else "metrics.csv"
        actual = pd.read_csv(root / filename)
        order = ["model", "split"] + (["label"] if name == "per_class" else [])
        pd.testing.assert_frame_equal(actual.sort_values(order).reset_index(drop=True),
                                      expected.sort_values(order).reset_index(drop=True),
                                      check_dtype=False, atol=1e-12, rtol=1e-12)
    matrices = confusion_matrices(predictions, split)
    for (model, partition), expected in matrices.items():
        actual = pd.read_csv(root / f"confusion_{model}_{partition}.csv", index_col=0)
        pd.testing.assert_frame_equal(actual, expected, check_names=False, check_dtype=False)
    return {"manifest": manifest, **recomputed, "matrices": matrices,
            "samples": pd.read_csv(root / "samples.csv"), "split": split, "predictions": predictions}


def build_prediction_figures(report):
    """Show class support, both F1 conventions and each held-out confusion matrix."""
    import matplotlib.pyplot as plt
    import numpy as np
    from reddit_sna.evaluation.metrics import LABELS

    figures = {}
    samples, split = report["samples"], report["split"]
    keys = ["reference_id", "feature_month", "community_id", "label_month"]
    labelled = samples.merge(split, on=keys, validate="one_to_one")
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    locations = np.arange(len(LABELS))
    for offset, partition in enumerate(("train", "validation", "test")):
        counts = labelled.loc[labelled["split"] == partition, "label"].value_counts()
        ax.bar(locations + (offset - 1) * .25, [counts.get(label, 0) for label in LABELS], .25, label=partition)
    ax.set(xticks=locations, xticklabels=LABELS, ylabel="Samples", title="Synthetic label support by temporal split")
    ax.legend()
    figures["support"] = fig
    rows = report["metrics"].query("split == 'test'").sort_values("model")
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    x = np.arange(len(rows))
    ax.bar(x - .18, rows["macro_f1"], .36, label="Macro-F1: present truth classes")
    ax.bar(x + .18, rows["macro_f1_six"], .36, label="Macro-F1: fixed six classes")
    ax.set(xticks=x, xticklabels=rows["model"], ylim=(0, 1), ylabel="F1", title="Synthetic test baselines; not Reddit performance")
    ax.legend()
    figures["baselines"] = fig
    for (model, partition), matrix in report["matrices"].items():
        if partition != "test":
            continue
        fig, ax = plt.subplots(figsize=(7, 6), layout="constrained")
        ax.imshow(matrix.to_numpy(), cmap="Blues", aspect="auto")
        for i in range(len(LABELS)):
            for j in range(len(LABELS)):
                ax.text(j, i, str(matrix.iloc[i, j]), ha="center", va="center")
        ax.set(xticks=range(6), xticklabels=LABELS, yticks=range(6), yticklabels=LABELS,
               xlabel="Predicted", ylabel="True synthetic label", title=f"{model}: test confusion")
        figures["confusion_" + model] = fig
    return figures
