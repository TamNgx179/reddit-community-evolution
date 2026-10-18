"""Verified descriptive forecast reports; never load persisted model pickles.

Every figure uses a checked schema-2 handoff. Zero-support classes stay visible;
tracker-derived labels and excluded cases are not social ground truth.
"""

from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path

from reddit_sna.contracts import Event
from reddit_sna.data.archive import digest_file
from reddit_sna.reporting.forecast_handoff import read_handoff


def summarize(run: Path) -> dict:
    """Read and validate the run before exposing aggregate and error tables."""
    delivery = read_handoff(run)
    metrics, quality = delivery["metrics"], delivery["quality"]
    order = [e.value for e in Event]
    models = []
    monthly = []
    for name, values in metrics["models"].items():
        models.append(dict(model=name, macro_f1=values["macro_f1"],
                           balanced_accuracy_present_classes=values["balanced_accuracy_present_classes"]))
        for month in sorted({r["label_month"] for r in delivery["predictions"]}):
            rows = [r for r in delivery["predictions"] if r["model"] == name and r["label_month"] == month]
            counts = Counter((r["y_true"], r["y_pred"]) for r in rows)
            f1 = []
            for label in order:
                denominator = sum(n for (a, _), n in counts.items() if a == label) + sum(n for (_, b), n in counts.items() if b == label)
                f1.append(2 * counts[label, label] / denominator if denominator else 0.0)
            monthly.append(dict(model=name, label_month=month, samples=len(rows), macro_f1=sum(f1) / len(f1)))
    return dict(delivery=delivery, models=models, monthly_scores=monthly,
                manifest_sha256=digest_file(run / "manifest.json"),
                coverage=dict(total_transitions=quality["total_source_transitions"],
                              eligible=quality["eligible_samples"], excluded=quality["unresolved"],
                              exclusion_fraction=quality["unresolved"] / quality["total_source_transitions"]),
                classes=[dict(event=label, train=quality["train_support"].get(label, 0),
                              test=quality["test_support"].get(label, 0)) for label in order])


def build_figures(report: dict) -> dict:
    """Return six named Figure families without displaying or writing them."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Install plotting dependencies with the project kernel: python -m pip install -e ".[notebook,forecast]"') from exc
    delivery = report["delivery"]
    classes = [r["event"] for r in report["classes"]]
    x = np.arange(len(classes))
    figures = {}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    for offset, split in ((-0.2, "train"), (0.2, "test")):
        axes[0].bar(x + offset, [r[split] for r in report["classes"]], 0.4, label=split)
    axes[0].set_xticks(x, classes, rotation=30)
    axes[0].set_title("Six-class pseudo-label support (zeroes retained)")
    axes[0].set_ylabel("Eligible community transitions")
    axes[0].legend()
    coverage = report["coverage"]
    axes[1].bar(["eligible", "excluded"], [coverage["eligible"], coverage["excluded"]], color=["steelblue", "darkorange"])
    axes[1].set_title(f"Excluded: {coverage['exclusion_fraction']:.2%} of source transitions")
    axes[1].set_ylabel("Source transitions")
    figures["support_and_coverage"] = fig

    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    names = [r["model"] for r in report["models"]]
    ax.bar(names, [r["macro_f1"] for r in report["models"]])
    ax.set(ylim=(0, 1), ylabel="Fixed-six-class macro-F1", title="Descriptive held-out baseline scores")
    figures["baseline_scores"] = fig

    fig, axes = plt.subplots(1, len(names), figsize=(7 * len(names), 4), squeeze=False, layout="constrained")
    for ax, name in zip(axes[0], names):
        values = delivery["metrics"]["models"][name]["per_class"]
        ax.bar(x - .2, [values[c]["recall"] for c in classes], .4, label="recall")
        ax.bar(x + .2, [values[c]["f1-score"] for c in classes], .4, label="F1")
        ax.set_xticks(x, classes, rotation=30)
        ax.set(ylim=(0, 1), title=name, ylabel="Class metric; absent support is zero")
        ax.legend()
    figures["per_class_metrics"] = fig

    fig, axes = plt.subplots(1, len(names), figsize=(7 * len(names), 5), squeeze=False, layout="constrained")
    for ax, name in zip(axes[0], names):
        matrix = delivery["metrics"]["models"][name]["confusion_matrix"]
        image = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks(x, classes, rotation=45, ha="right")
        ax.set_yticks(x, classes)
        ax.set(title=name, xlabel="Predicted pseudo-label", ylabel="Observed tracker pseudo-label")
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, str(matrix[i][j]), ha="center", va="center", fontsize=8,
                        color="white" if matrix[i][j] > np.max(matrix) / 2 else "black")
        fig.colorbar(image, ax=ax, label="Held-out samples")
    figures["confusion_matrices"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    support = delivery["quality"]["monthly_support"]
    months = list(support)
    bottom = np.zeros(len(months))
    for label in classes + ["unresolved"]:
        values = [support[m].get(label, 0) for m in months]
        axes[0].bar(months, values, bottom=bottom, label=label)
        bottom += values
    axes[0].tick_params(axis="x", rotation=60)
    axes[0].set(title="Label-month support including exclusions", ylabel="Source transitions")
    axes[0].legend(fontsize=7)
    for name in names:
        rows = [r for r in report["monthly_scores"] if r["model"] == name]
        axes[1].plot([r["label_month"] for r in rows], [r["macro_f1"] for r in rows], marker="o", label=name)
    axes[1].set(ylim=(0, 1), title="Held-out monthly diagnostics", ylabel="Six-class macro-F1")
    axes[1].legend(fontsize=8)
    figures["monthly_diagnostics"] = fig

    fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
    folds = delivery["development_folds"]
    if not folds:
        ax.text(.5, .5, "No development folds: insufficient training label months", ha="center", va="center", transform=ax.transAxes)
    else:
        for name in sorted({n for fold in folds for n in fold["models"]}):
            selected = [f for f in folds if name in f["models"]]
            ax.plot([f["test_start_label_month"] for f in selected], [f["models"][name]["macro_f1"] for f in selected], marker="o", label=name)
        ax.legend(fontsize=8)
    ax.set(ylim=(0, 1), title="Expanding-window development only (not independent test repeats)", ylabel="Six-class macro-F1")
    figures["development_folds"] = fig
    return figures


def export_report(run: Path, output: Path, artifact_root: Path) -> Path:
    """Write an immutable, source-bound JSON report and PNG/SVG figure set."""
    output, artifact_root = output.resolve(), artifact_root.resolve()
    if not output.is_relative_to(artifact_root) or output == artifact_root:
        raise ValueError("Report output must be a child of artifacts")
    if output.is_relative_to(run.resolve()):
        raise ValueError("Report output must not modify its immutable forecast source")
    if output.exists():
        raise FileExistsError("Report output already exists")
    report = summarize(run)
    figures = build_figures(report)
    output.mkdir(parents=True, exist_ok=False)
    from matplotlib import pyplot as plt
    try:
        for name, figure in figures.items():
            figure.savefig(output / f"{name}.png", dpi=160)
            figure.savefig(output / f"{name}.svg")
        summary = {k: v for k, v in report.items() if k != "delivery"}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if digest_file(run / "manifest.json") != report["manifest_sha256"]:
            raise ValueError("Forecast manifest changed during report generation")
        read_handoff(run)
        manifest = dict(status="complete", forecast_manifest_sha256=report["manifest_sha256"],
                        label_reference_id=report["delivery"]["manifest"]["label_reference_id"],
                        source_hashes={"forecast.py": digest_file(Path(__file__)),
                                       "forecast_handoff.py": digest_file(Path(__file__).with_name("forecast_handoff.py"))},
                        plotting_versions={name: version(name) for name in ("matplotlib", "numpy")},
                        figures=list(figures), interpretation="descriptive pseudo-label prediction; not social ground truth",
                        artifact_hashes={p.name: digest_file(p) for p in output.iterdir()})
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        (output / "manifest.json").write_text(json.dumps({"status": "failed"}) + "\n", encoding="utf-8")
        raise
    finally:
        for figure in figures.values():
            plt.close(figure)
    return output
