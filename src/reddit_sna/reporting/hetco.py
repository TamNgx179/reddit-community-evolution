"""Figures for a completed HeTCo v1 run; scores are read, never hardcoded."""

import csv
import json
from pathlib import Path

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import EVENTS
from reddit_sna.features.members import MEMBER_FEATURES


def read_hetco(run):
    run = Path(run).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError("HeTCo run is not complete")
    for name, digest in manifest["artifact_hashes"].items():
        if digest_file(run / name) != digest:
            raise ValueError(f"HeTCo artifact changed: {name}")
    with (run / "attention.csv").open(encoding="utf-8", newline="") as stream:
        attention = list(csv.DictReader(stream))
    with (run / "monthly.csv").open(encoding="utf-8", newline="") as stream:
        monthly = list(csv.DictReader(stream))
    evaluation = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
    return dict(manifest=manifest, evaluation=evaluation, attention=attention, monthly=monthly)


def build_figures(delivery):
    """Comparison, ablation intervals, rolling months, confusion and attention profile."""
    import numpy as np
    import matplotlib.pyplot as plt
    ev, figures = delivery["evaluation"], {}
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, window in zip(axes, ("main", "rolling")):
        rows = [r for r in ev["comparison"] if r["window"] == window][::-1]
        y = np.arange(len(rows))
        ax.barh(y - .18, [r["mean_macro_f1_six"] for r in rows], .36, label="macro-F1 (six classes)")
        ax.barh(y + .18, [r["mean_balanced_accuracy"] for r in rows], .36, label="balanced accuracy")
        ax.set_yticks(y, [r["model"] for r in rows]); ax.set_title(f"{window} window, mean of three seeds")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.0, -0.06), ncol=2)
    figures["comparison"] = fig
    fig, ax = plt.subplots(figsize=(10, 4.5))
    intervals = ev["intervals"]
    for i, r in enumerate(intervals):
        ax.plot([r["low"], r["high"]], [i, i], marker="|", color="tab:blue")
    ax.axvline(0, color="black")
    ax.set_yticks(range(len(intervals)), [f'{r["model"]} - {r["reference"]}' for r in intervals])
    ax.set_xlabel("95% rolling-month block-bootstrap interval of the macro-F1 difference")
    ax.set_title("Inspected 2015 rolling months; exploratory, not confirmatory")
    figures["intervals"] = fig
    fig, ax = plt.subplots(figsize=(10, 4))
    months = sorted({r["month"] for r in delivery["monthly"]})
    present = {r["model"] for r in delivery["monthly"]}
    for name in [n for n in ("B4_logreg", "HeTCo_v0", "HeTCo_v1", "HeTCo_v2", "A7_mean_pool") if n in present]:
        values = [np.mean([float(r["macro_f1_six"]) for r in delivery["monthly"]
                           if r["model"] == name and r["month"] == m]) for m in months]
        ax.plot(months, values, marker="o", label=name)
    ax.set_ylabel("Mean six-class macro-F1"); ax.set_title("Rolling origins: fit earlier label months only")
    ax.legend()
    figures["monthly"] = fig
    shown = [n for n in ("HeTCo_v2", "HeTCo_v1", "A7_mean_pool") if n in ev["main_confusion_pooled_seeds"]][:2]
    fig, axes = plt.subplots(1, len(shown), figsize=(5.5 * len(shown), 4), squeeze=False)
    for ax, name in zip(axes[0], shown):
        matrix = ev["main_confusion_pooled_seeds"][name]
        ax.imshow(matrix, cmap="Blues"); ax.set_xticks(range(6), EVENTS, rotation=45, ha="right")
        ax.set_yticks(range(6), EVENTS); ax.set_title(name + " / three seeds pooled")
        ax.set_xlabel("Predicted"); ax.set_ylabel("Truth")
        for i in range(6):
            for j in range(6):
                ax.text(j, i, str(matrix[i][j]), ha="center", va="center", fontsize=8)
    figures["confusion"] = fig
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    shift = [np.mean([float(r[f"weighted_{f}"]) - float(r[f"mean_{f}"]) for r in delivery["attention"]])
             for f in MEMBER_FEATURES]
    axes[0].barh(MEMBER_FEATURES[::-1], shift[::-1]); axes[0].axvline(0, color="black")
    axes[0].set_xlabel("Attention-weighted minus uniform member mean (raw units)")
    axes[0].set_title("Which members HeTCo v1 attends to")
    sizes = [int(r["size"]) for r in delivery["attention"]]
    axes[1].scatter(sizes, [float(r["effective_members"]) / int(r["size"]) for r in delivery["attention"]], s=8)
    axes[1].set_xscale("log"); axes[1].set_xlabel("Community size"); axes[1].set_ylabel("Effective members / size")
    axes[1].set_title("Attention concentration (1 = uniform)")
    figures["attention"] = fig
    for fig in figures.values():
        fig.tight_layout()
    return figures


def export_figures(run, output):
    """Write PNG figures into a new directory separate from the run."""
    run, output = Path(run).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError("HeTCo figure output must be new and separate from run")
    figures = build_figures(read_hetco(run))
    import matplotlib.pyplot as plt
    output.mkdir(parents=True)
    try:
        for name, fig in figures.items():
            fig.savefig(output / f"{name}.png", dpi=140)
    finally:
        for fig in figures.values():
            plt.close(fig)
    return output
