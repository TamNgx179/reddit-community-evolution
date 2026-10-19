"""Replay verified synthetic outputs for a notebook; never run a producer."""

import csv
from hashlib import sha256
from html import escape
from importlib.metadata import version
import json
import math
from pathlib import Path, PurePosixPath
import platform

from reddit_sna.reporting.synthetic_handoff import SCENARIOS, inspect_synthetic_handoff


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(path):
    return sha256(path.read_bytes()).hexdigest()


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = list(reader)
    _require(rows and all(None not in r and all(v is not None for v in r.values()) for r in rows),
             f"missing or invalid report rows: {path.name}")
    return rows


def _number(value):
    if value is None or value == "":
        return None
    _require(not isinstance(value, bool), "boolean is not a metric")
    value = float(value)
    _require(math.isfinite(value), "nonfinite recorded metric")
    return value


def table_html(rows: list[dict], columns=None) -> str:
    """Small escaped notebook table; blank/None stays a visible missing marker."""
    if not rows:
        return "<p>No rows.</p>"
    columns = list(rows[0]) if columns is None else columns
    def cell(value):
        if value is None or value == "":
            return "—"
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    header = "".join(f"<th>{escape(str(c))}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(cell(r[c]))}</td>" for c in columns) + "</tr>" for r in rows)
    return '<div style="overflow-x:auto"><table><thead><tr>' + header + "</tr></thead><tbody>" + body + "</tbody></table></div>"


def verify_delivery(bundle: Path, expected_sha256: str) -> dict:
    """Check the pinned T02 manifest and all declared bytes; ignore root extras.

    Recipient-created check-* directories may coexist with the bundle. Only
    declared input files are read; complete run inventories are checked again
    by the independent consumer. This does not re-certify a frozen runtime.
    """
    bundle = Path(bundle).resolve()
    path = bundle / "delivery-manifest.json"
    _require(_sha(path) == expected_sha256, "delivery manifest SHA-256 mismatch")
    manifest = _json(path)
    _require(manifest["schema_version"] == 1 and manifest["status"] == "complete"
             and manifest["artifact_type"] == "phuc-dang-synthetic-data-handoff", "unsupported delivery")
    _require(set(manifest["source_manifest_sha256"]) == {"development", "evaluation"}, "missing source pins")
    for name, info in manifest["files"].items():
        relative = PurePosixPath(name)
        _require(not relative.is_absolute() and relative.as_posix() == name and relative.parts
                 and ".." not in relative.parts and "\\" not in name and ":" not in name, "unsafe delivery path")
        source = bundle / name
        _require(source.resolve().is_relative_to(bundle) and not source.is_symlink(), "unsafe delivery file")
        _require(_sha(source) == info["sha256"] and source.stat().st_size == info["bytes"],
                 f"delivery file changed: {name}")
    return manifest


def summary_view(rows: list[dict]) -> list[dict]:
    """Read recorded means and supports; preserve missing values and seed roles."""
    result = []
    seen = set()
    for row in rows:
        seed = int(row["detector_seed"])
        key = row["split"], row["aggregation_level"], row["scenario"], seed
        _require(key not in seen, "duplicate summary key")
        seen.add(key)
        _require(seed in (0, 1, 2) and row["seed_role"] == ("canonical" if seed == 0 else "diagnostic"),
                 "canonical seed must remain 0")
        total, valid, missing = (int(row[k]) for k in ("n_rows", "n_ami_valid", "n_ami_missing"))
        mean, coverage = _number(row["ami_mean"]), _number(row["coverage_mean"])
        _require(min(total, valid, missing) >= 0 and valid + missing == total, "AMI support mismatch")
        _require((mean is None) == (valid == 0) and (mean is None or -1 <= mean <= 1), "AMI mean/support mismatch")
        _require(coverage is None or 0 <= coverage <= 1, "coverage outside [0,1]")
        result.append({"split": row["split"], "level": row["aggregation_level"], "scenario": row["scenario"],
                       "detector_seed": seed, "seed_role": row["seed_role"], "n_rows": total,
                       "n_ami_valid": valid, "n_ami_missing": missing, "ami_mean": mean,
                       "coverage_mean": coverage, "missing_reasons": row["ami_missing_reasons"]})
    return result


def timing_view(manifest: dict, split: str) -> list[dict]:
    """Original wall times retain their wrapper scope, including all three seeds."""
    result = []
    for stage in ("generation", "detection", "evaluation"):
        seconds = _number(manifest["stages"][stage]["wall_seconds"])
        _require(seconds is not None and seconds >= 0, "invalid recorded stage time")
        result.append({"split": split, "phase": stage, "wall_seconds": seconds,
                       "scope": manifest["timing"]["stage_scope"]})
    seconds = _number(manifest["timing"]["run_wall_seconds"])
    _require(seconds is not None and seconds >= 0, "invalid recorded run time")
    result.append({"split": split, "phase": "run_total", "wall_seconds": seconds,
                   "scope": manifest["timing"]["run_scope"]})
    return result


def _network(bundle, inventory, dataset_id, metric_rows):
    records = [r for r in inventory["snapshot_memberships"] if r["dataset_id"] == dataset_id and r["canonical"]]
    _require(len(records) == 2, "selected dataset must have two canonical snapshots")
    split = inventory["split"]
    run = bundle / "runs" / split
    snapshots, sources = [], set()
    for record in records:
        month = record["month"]
        nodes = [r["user_id"] for r in _csv(run / record["nodes_file"])]
        with (run / record["graph_file"]).open(encoding="utf-8", newline="") as stream:
            edges = [(r["source_user_id"], r["target_user_id"]) for r in csv.DictReader(stream)]
        truth = {r["user_id"]: r["community_id"] for r in _csv(run / record["truth_membership_file"]) if r["month"] == month}
        with (run / record["detector_membership_file"]).open(encoding="utf-8", newline="") as stream:
            predicted = {r["user_id"]: r["community_id"] for r in csv.DictReader(stream)}
        metric = next(r for r in metric_rows if r["dataset_id"] == dataset_id and r["month"] == month and r["detector_seed"] == "0")
        _require(set(nodes) == set(truth) and set(predicted) == {u for e in edges for u in e},
                 "network display coverage mismatch")
        snapshots.append({"month": month, "nodes": nodes, "edges": edges, "truth": truth,
                          "predicted": predicted, "metric": metric, "mapping": record})
        sources.update(f"runs/{split}/{record[k]}" for k in
                       ("nodes_file", "graph_file", "truth_membership_file", "detector_membership_file"))
    return {"dataset_id": dataset_id, "split": split, "snapshots": snapshots}, sorted(sources)


def load_synthetic_demo(bundle: Path, *, expected_delivery_sha256: str,
                        dataset_id: str = "dev-grow-easy-g11") -> dict:
    """Audit existing development/evaluation runs, then expose recorded data."""
    bundle = Path(bundle).resolve()
    delivery = verify_delivery(bundle, expected_delivery_sha256)
    inventories, manifests, recipes, environments = {}, {}, {}, {}
    metrics, summaries, timings = [], [], []
    sources = {"quality": [], "seeds": [], "timing": []}
    for split in ("development", "evaluation"):
        run = bundle / "runs" / split
        inventories[split] = inspect_synthetic_handoff(run, expected_manifest_sha256=delivery["source_manifest_sha256"][split])
        manifest = manifests[split] = _json(run / "manifest.json")
        recipes[split] = _json(run / manifest["config_inputs"]["benchmark"]["archive"])
        environments[split] = _json(run / "provenance/environment.json")
        rows = _csv(run / "evaluation/detection_metrics.csv")
        expected = {(r["dataset_id"], r["month"], r["detector_seed"]): r
                    for r in inventories[split]["snapshot_memberships"]}
        seen = set()
        for row in rows:
            key = row["dataset_id"], row["month"], int(row["detector_seed"])
            _require(key in expected and key not in seen, "metric key mismatch")
            seen.add(key)
            mapping = expected[key]
            _require(row["split"] == split and row["truth_reference"] == mapping["truth_reference"]
                     and row["detector_reference"] == mapping["detector_reference"]
                     and row["canonical"] == str(key[2] == 0), "metric reference/canonical mismatch")
            ami = _number(row["ami"])
            _require((ami is None) == (row["ami_status"] != "ok") and (ami is None or -1 <= ami <= 1),
                     "invalid recorded AMI/status")
            _require(ami is not None or row["ami_reason"], "missing AMI reason")
        _require(seen == set(expected), "metric keys incomplete")
        metrics.extend(rows)
        summary = _csv(run / "evaluation/detection_summary.csv")
        view = summary_view(summary)
        required = {(level, scenario, seed) for level, scenarios in
                    (("all_scenarios", ("",)), ("scenario", SCENARIOS)) for scenario in scenarios for seed in (0, 1, 2)}
        _require({(r["level"], r["scenario"], r["detector_seed"]) for r in view} == required
                 and all(r["split"] == split for r in view), "summary schedule mismatch")
        summaries.extend(summary)
        timings.extend(timing_view(manifest, split))
        for kind in ("quality", "seeds"):
            sources[kind].append(f"runs/{split}/evaluation/detection_summary.csv")
        sources["timing"].append(f"runs/{split}/manifest.json")
    selected = next((i for i in inventories.values() if dataset_id in i["dataset_ids"]), None)
    _require(selected is not None, "selected dataset is not in verified runs")
    network, sources["network"] = _network(bundle, selected, dataset_id, metrics)
    verify_delivery(bundle, expected_delivery_sha256)
    return {"bundle": bundle, "delivery_sha256": expected_delivery_sha256, "delivery": delivery,
            "inventories": inventories, "manifests": manifests, "recipes": recipes, "environments": environments,
            "metrics": metrics, "summaries": summaries, "summary_view": summary_view(summaries),
            "timings": timings, "network": network, "figure_inputs": sources}


def build_synthetic_figures(demo: dict) -> dict:
    """Full selected graphs and recorded summaries; no partitioning or sampling."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    import numpy as np

    figures = {}
    palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
    snapshots = demo["network"]["snapshots"]
    users = sorted({u for s in snapshots for u in s["nodes"]})
    angles = np.linspace(0, 2 * np.pi, max(1, len(users)), endpoint=False)
    positions = {u: (np.cos(a), np.sin(a)) for u, a in zip(users, angles)}
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), layout="constrained")
    for row, snapshot in enumerate(snapshots):
        for col, kind in enumerate(("truth", "predicted")):
            ax = axes[row, col]
            mapping = snapshot[kind]
            groups = sorted(set(mapping.values()))
            colors = {g: palette[i % len(palette)] for i, g in enumerate(groups)}
            ax.add_collection(LineCollection([[positions[a], positions[b]] for a, b in snapshot["edges"]],
                                             colors="#687482", linewidths=.65, alpha=.32))
            for group in groups:
                points = [positions[u] for u in snapshot["nodes"] if mapping.get(u) == group]
                ax.scatter(*zip(*points), color=colors[group], s=78, edgecolors="white", linewidths=.7, zorder=3)
            isolated = [positions[u] for u in snapshot["nodes"] if u not in mapping]
            if isolated:
                ax.scatter(*zip(*isolated), color="#666666", marker="x", s=65, zorder=4)
            for u in snapshot["nodes"]:
                x, y = positions[u]
                ax.text(x * 1.12, y * 1.12, u, fontsize=7, ha="center", va="center")
            handles = [Line2D([], [], color=c, marker="o", linestyle="", label=f"local group {g}") for g, c in colors.items()]
            if isolated:
                handles.append(Line2D([], [], color="#666666", marker="x", linestyle="", label="unassigned isolate"))
            ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.01), ncol=3, fontsize=8)
            ax.set(xlim=(-1.4, 1.4), ylim=(-1.4, 1.4), aspect="equal")
            ax.axis("off")
            title = "Planted truth" if kind == "truth" else "Leiden seed 0"
            ax.set_title(f"{snapshot['month']} | {title}\n{len(snapshot['nodes'])} active nodes, {len(snapshot['edges'])} edges")
    fig.suptitle(demo["network"]["dataset_id"] + " | full graphs, shared user positions\nColors are local to each panel; group IDs are not matched", fontsize=12)
    figures["01_network"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    x = np.arange(len(SCENARIOS))
    for offset, split, color in ((-.19, "development", palette[0]), (.19, "evaluation", palette[1])):
        rows = [next(r for r in demo["summary_view"] if r["split"] == split and r["level"] == "scenario"
                     and r["scenario"] == case and r["detector_seed"] == 0) for case in SCENARIOS]
        for ax, field in zip(axes, ("ami_mean", "coverage_mean")):
            values = [np.nan if r[field] is None else r[field] for r in rows]
            ax.bar(x + offset, values, .36, color=color, label=split)
            ax.set_xticks(x, SCENARIOS, rotation=20)
            ax.axhline(0, color="#555555", linewidth=.6)
        for i, r in enumerate(rows):
            label = f"{r['n_ami_valid']}/{r['n_rows']}"
            axes[0].text(i + offset, (r["ami_mean"] or 0) + .025, label, ha="center", fontsize=8)
    axes[0].set(title="AMI mean | labels: valid / total rows", ylabel="Recorded AMI", ylim=(-.05, 1.16))
    axes[1].set(title="Coverage | all active users in denominator", ylabel="Assigned / active", ylim=(0, 1.12))
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=2)
    fig.suptitle("Canonical seed 0, each split separate; null AMI excluded from mean, retained in support")
    figures["02_quality"] = fig

    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for split, color in (("development", palette[0]), ("evaluation", palette[1])):
        rows = sorted((r for r in demo["summary_view"] if r["split"] == split and r["level"] == "all_scenarios"),
                      key=lambda r: r["detector_seed"])
        ax.plot([r["detector_seed"] for r in rows], [np.nan if r["ami_mean"] is None else r["ami_mean"] for r in rows],
                "o-", color=color, label=split)
    ax.set(xticks=[0, 1, 2], xticklabels=["0 (canonical)", "1 (diagnostic)", "2 (diagnostic)"],
           ylabel="Recorded AMI mean (valid rows)", title="Repeatability diagnostics | canonical fixed before scores")
    ax.legend(); ax.grid(alpha=.2)
    figures["03_seeds"] = fig

    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    phases = ("generation", "detection", "evaluation")
    x = np.arange(len(phases))
    for offset, split, color in ((-.19, "development", palette[0]), (.19, "evaluation", palette[1])):
        values = [next(r["wall_seconds"] for r in demo["timings"] if r["split"] == split and r["phase"] == phase) for phase in phases]
        bars = ax.bar(x + offset, values, .36, label=split, color=color)
        ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    ax.set(xticks=x, xticklabels=phases, ylabel="Recorded wall seconds",
           title="Original run stages | wrapper times, detection includes all three seeds")
    ax.legend(); ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    figures["04_timing"] = fig
    return figures


def export_synthetic_demo(demo: dict, figures: dict, output: Path, *, notebook: Path) -> dict:
    """Save new tables/figures with source hashes; complete metadata published last."""
    output, bundle, notebook = Path(output).resolve(), demo["bundle"], Path(notebook).resolve()
    _require(not output.exists(), "demo output already exists")
    _require(not output.is_relative_to(bundle) and not bundle.is_relative_to(output), "demo output overlaps input")
    _require(set(figures) == {"01_network", "02_quality", "03_seeds", "04_timing"}, "incomplete figure set")
    verify_delivery(bundle, demo["delivery_sha256"])
    output.mkdir()
    def write_json(path, value):
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False); stream.write("\n")
    def write_table(path, rows):
        with path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
    try:
        (output / "figures").mkdir(); (output / "tables").mkdir()
        for name, rows in (("metrics", demo["metrics"]), ("summary", demo["summaries"]),
                           ("summary-view", demo["summary_view"]), ("timing", demo["timings"])):
            write_table(output / "tables" / f"{name}.csv", rows)
        captions = {}
        for name, fig in figures.items():
            kind = name.split("_", 1)[1]
            for suffix in ("png", "svg"):
                fig.savefig(output / "figures" / f"{name}.{suffix}", dpi=150, facecolor="white")
            captions[name] = {"inputs": {p: demo["delivery"]["files"][p] for p in demo["figure_inputs"][kind]},
                              "scope": "full selected graph" if kind == "network" else "recorded full-run results",
                              "canonical_seed": 0, "no_new_detection_or_metric_computation": True}
        write_json(output / "figure-sources.json", captions)
        verify_delivery(bundle, demo["delivery_sha256"])
        source = Path(__file__)
        handoff = Path(inspect_synthetic_handoff.__code__.co_filename)
        metadata = {"schema_version": 1, "artifact_type": "synthetic-notebook-replay", "status": "complete",
                    "scope": "recorded detection only; tracker/forecasting not implemented", "partner_acceptance": "not_verified",
                    "delivery_manifest_sha256": demo["delivery_sha256"],
                    "source_manifest_sha256": demo["delivery"]["source_manifest_sha256"],
                    "source_files": {"synthetic_demo.py": _sha(source), "synthetic_handoff.py": _sha(handoff),
                                     "01_synthetic_demo.ipynb": _sha(notebook)},
                    "runtime": {"python": platform.python_version(), "matplotlib": version("matplotlib"), "numpy": version("numpy")},
                    "selected_dataset": demo["network"]["dataset_id"], "canonical_seed": 0,
                    "metric_rows": len(demo["metrics"]), "summary_rows": len(demo["summaries"]),
                    "figure_count": len(figures), "peak_memory_bytes": None,
                    "files": {p.relative_to(output).as_posix(): {"sha256": _sha(p), "bytes": p.stat().st_size}
                              for p in sorted(output.rglob("*")) if p.is_file()}}
        write_json(output / "metadata.json", metadata)
        return metadata
    except Exception as exc:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(exc).__name__, "message": str(exc)})
        raise
