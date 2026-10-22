"""Post-hoc descriptions of verified saved partitions, without running a scorer."""

from collections import Counter
import csv
from itertools import combinations, combinations_with_replacement
import json
from pathlib import Path

from reddit_sna.reporting.synthetic_demo import _network, _number, _require, _sha, verify_delivery


def select_case_rows(metrics: list[dict], split: str = "development") -> list[dict]:
    """Fixed canonical seed; deterministic post-hoc examples, never a new test set."""
    rows = [r for r in metrics if r["split"] == split and int(r["detector_seed"]) == 0]
    _require(rows and all(str(r["canonical"]) == "True" for r in rows), "canonical seed must remain 0")
    _require(len({(r["dataset_id"], r["month"]) for r in rows}) == len(rows), "duplicate case key")
    valid = sorted((r for r in rows if _number(r["ami"]) is not None),
                   key=lambda r: (_number(r["ami"]), r["dataset_id"], r["month"]))
    missing = sorted((r for r in rows if _number(r["ami"]) is None),
                     key=lambda r: (r["dataset_id"], r["month"]))
    _require(valid, "no valid canonical AMI for hard-case selection")
    _require(all(r["ami_status"] == "ok" for r in valid)
             and all(r["ami_status"] != "ok" and r["ami_reason"] for r in missing), "AMI status/reason mismatch")
    chosen = [{"kind": "hard", "metric": valid[0],
               "selection": "lowest recorded non-null canonical AMI, then dataset_id/month within split",
               "tied_minimum_rows": sum(_number(r["ami"]) == _number(valid[0]["ami"]) for r in valid)}]
    if missing:
        chosen.append({"kind": "null", "metric": missing[0],
                       "selection": "first recorded canonical null by dataset_id/month within split",
                       "tied_minimum_rows": None})
    return chosen


def describe_snapshot(snapshot: dict) -> dict:
    """Count users, pair disagreements and edge blocks; group names are local.

    Pair disagreements use assigned users only and are descriptions of a static
    partition, not tracking events or event-F1. Unassigned isolates stay explicit
    in the contingency table and active-user denominator.
    """
    nodes, edges, truth, predicted = (snapshot[k] for k in ("nodes", "edges", "truth", "predicted"))
    _require(len(nodes) == len(set(nodes)) and set(nodes) == set(truth), "active/truth user keys mismatch")
    endpoints = {u for edge in edges for u in edge}
    _require(endpoints <= set(nodes) and set(predicted) == endpoints, "predicted users must equal endpoints")
    _require(all(a != b for a, b in edges) and len({tuple(sorted(e)) for e in edges}) == len(edges),
             "graph must be undirected simple without self-loops")
    true_groups = sorted(set(truth.values()))
    pred_groups = sorted(set(predicted.values()))
    columns = pred_groups + ([None] if set(nodes) - set(predicted) else [])
    contingency = [{"truth_group": a, "predicted_group": b, "assigned": b is not None,
                    "users": sum(truth[u] == a and predicted.get(u) == b for u in nodes)}
                   for a in true_groups for b in columns]
    split_pairs = merged_pairs = 0
    for a, b in combinations(sorted(predicted), 2):
        split_pairs += truth[a] == truth[b] and predicted[a] != predicted[b]
        merged_pairs += truth[a] != truth[b] and predicted[a] == predicted[b]
    sizes = Counter(predicted.values())
    edge_counts = Counter(tuple(sorted((predicted[a], predicted[b]))) for a, b in edges)
    blocks = []
    for a, b in combinations_with_replacement(pred_groups, 2):
        possible = sizes[a] * (sizes[a] - 1) // 2 if a == b else sizes[a] * sizes[b]
        blocks.append({"predicted_group_a": a, "predicted_group_b": b,
                       "users_a": sizes[a], "users_b": sizes[b], "edges": edge_counts[a, b],
                       "possible_edges": possible, "density": edge_counts[a, b] / possible if possible else None})
    return {"active_nodes": len(nodes), "edges": len(edges), "assigned_nodes": len(predicted),
            "unassigned_nodes": len(nodes) - len(predicted), "truth_groups": len(true_groups),
            "predicted_groups": len(pred_groups), "scored_pairs": len(predicted) * (len(predicted) - 1) // 2,
            "truth_same_pred_different_pairs": split_pairs, "truth_different_pred_same_pairs": merged_pairs,
            "contingency": contingency, "edge_blocks": blocks}


def analyze_synthetic_cases(demo: dict, split: str = "development") -> list[dict]:
    """Use only the verified bundle behind load_synthetic_demo, then verify again."""
    verify_delivery(demo["bundle"], demo["delivery_sha256"])
    cases = []
    for selection in select_case_rows(demo["metrics"], split):
        metric = selection["metric"]
        network, _ = _network(demo["bundle"], demo["inventories"][split], metric["dataset_id"], demo["metrics"])
        snapshot = next(s for s in network["snapshots"] if s["month"] == metric["month"])
        description = describe_snapshot(snapshot)
        for key in ("active_nodes", "assigned_nodes", "predicted_communities"):
            actual = description["predicted_groups" if key == "predicted_communities" else key]
            _require(actual == int(metric[key]), f"saved case count mismatch: {key}")
        _require(description["truth_groups"] == int(metric["true_communities_all_nodes"]), "truth count mismatch")
        paths = [f"runs/{split}/{snapshot['mapping'][k]}" for k in
                 ("nodes_file", "graph_file", "truth_membership_file", "detector_membership_file")]
        paths += [f"runs/{split}/evaluation/{name}" for name in ("detection_metrics.csv", "ami-policy.json")]
        cases.append(dict(selection, split=split, dataset_id=metric["dataset_id"], month=metric["month"],
                          canonical_seed=0, snapshot=snapshot, description=description,
                          inputs={p: demo["delivery"]["files"][p] for p in sorted(paths)}))
    verify_delivery(demo["bundle"], demo["delivery_sha256"])
    return cases


def case_summary(cases: list[dict]) -> list[dict]:
    return [{"kind": c["kind"], "split": c["split"], "dataset_id": c["dataset_id"], "month": c["month"],
             "detector_seed": 0, "ami": _number(c["metric"]["ami"]), "ami_status": c["metric"]["ami_status"],
             "ami_reason": c["metric"]["ami_reason"], "coverage": _number(c["metric"]["coverage"]),
             **{k: v for k, v in c["description"].items() if k not in ("contingency", "edge_blocks")},
             "selection": c["selection"], "tied_minimum_rows": c["tied_minimum_rows"]} for c in cases]


def build_case_figures(cases: list[dict]) -> dict:
    """Full graph truth/prediction and a user-count contingency (not event confusion)."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    import numpy as np

    figures = {}
    palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
    for case in cases:
        s = case["snapshot"]
        nodes = sorted(s["nodes"])
        angles = np.linspace(0, 2 * np.pi, max(1, len(nodes)), endpoint=False)
        pos = {u: (np.cos(a), np.sin(a)) for u, a in zip(nodes, angles)}
        fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained", width_ratios=[1.2, 1.2, 1])
        for ax, kind in zip(axes[:2], ("truth", "predicted")):
            mapping = s[kind]
            groups = sorted(set(mapping.values()))
            ax.add_collection(LineCollection([[pos[a], pos[b]] for a, b in s["edges"]],
                                             colors="#687482", linewidths=.65, alpha=.32))
            handles = []
            for i, group in enumerate(groups):
                points = [pos[u] for u in nodes if mapping.get(u) == group]
                color = palette[i % len(palette)]
                ax.scatter(*zip(*points), color=color, s=65, edgecolors="white", linewidths=.6, zorder=3)
                handles.append(Line2D([], [], color=color, marker="o", linestyle="", label=f"{group}: {len(points)} users"))
            isolated = [pos[u] for u in nodes if u not in mapping]
            if isolated:
                ax.scatter(*zip(*isolated), color="#666666", marker="x", s=65, zorder=3)
                handles.append(Line2D([], [], color="#666666", marker="x", linestyle="", label="unassigned isolate"))
            for u, (x, y) in pos.items():
                ax.text(x * 1.12, y * 1.12, u, fontsize=6, ha="center", va="center")
            ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.02), fontsize=8, ncol=2)
            ax.set(xlim=(-1.4, 1.4), ylim=(-1.4, 1.4), aspect="equal", title="Planted truth" if kind == "truth" else "Leiden seed 0")
            ax.axis("off")
        rows = case["description"]["contingency"]
        truth = sorted({r["truth_group"] for r in rows})
        pred = sorted({r["predicted_group"] for r in rows if r["assigned"]})
        if any(not r["assigned"] for r in rows):
            pred.append(None)
        counts = {(r["truth_group"], r["predicted_group"]): r["users"] for r in rows}
        matrix = np.array([[counts[a, b] for b in pred] for a in truth])
        ax = axes[2]
        if matrix.size:
            ax.imshow(matrix, cmap="Blues", vmin=0, aspect="auto")
            for i, a in enumerate(truth):
                for j, b in enumerate(pred):
                    value = counts[a, b]
                    ax.text(j, i, str(value), ha="center", va="center", color="white" if value > matrix.max() / 2 else "black")
        ax.set(xticks=range(len(pred)), xticklabels=["unassigned" if p is None else p for p in pred],
               yticks=range(len(truth)), yticklabels=truth, xlabel="Predicted local group", ylabel="Truth group",
               title="User-count contingency\nIDs/colors are local, not matched")
        ami = case["metric"]["ami"] or f"null ({case['metric']['ami_reason']})"
        fig.suptitle(f"{case['dataset_id']} | {case['month']} | {len(nodes)} active users, {len(s['edges'])} edges\n"
                     f"Recorded AMI: {ami} | post-hoc example; no detector/scorer rerun", fontsize=12)
        figures[case["kind"]] = fig
    return figures


def export_case_analysis(demo: dict, cases: list[dict], figures: dict, output: Path, *, notebook: Path) -> dict:
    """Publish a separate new analysis directory; retain partial output on failure."""
    output, bundle = Path(output).resolve(), demo["bundle"].resolve()
    _require(not output.exists(), "analysis output already exists")
    _require(not output.is_relative_to(bundle) and not bundle.is_relative_to(output), "analysis output overlaps input")
    _require(cases and len({c["kind"] for c in cases}) == len(cases)
             and set(figures) == {c["kind"] for c in cases}, "analysis figure/case mismatch")
    verify_delivery(bundle, demo["delivery_sha256"])
    output.mkdir()

    def write_json(name, value):
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
            stream.write("\n")

    def write_csv(name, rows):
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)

    try:
        write_json("analysis.json", cases)
        write_csv("case-summary.csv", case_summary(cases))
        for c in cases:
            for key in ("contingency", "edge_blocks"):
                if c["description"][key]:
                    write_csv(f"{c['kind']}-{key}.csv", c["description"][key])
            for suffix in ("png", "svg"):
                figures[c["kind"]].savefig(output / f"{c['kind']}.{suffix}", dpi=150, facecolor="white")
        write_json("figure-sources.json", {c["kind"]: {"inputs": c["inputs"], "selection": c["selection"],
                   "dataset_id": c["dataset_id"], "month": c["month"], "split": c["split"],
                   "scope": "full graph truth/prediction and user contingency; not event confusion"} for c in cases})
        verify_delivery(bundle, demo["delivery_sha256"])
        metadata = {"schema_version": 1, "artifact_type": "synthetic-posthoc-case-analysis", "status": "complete",
                    "canonical_seed": 0, "delivery_manifest_sha256": demo["delivery_sha256"],
                    "scope": "post-hoc static detection descriptions; no new AMI/event-F1, no retuning",
                    "partner_acceptance": "not_verified", "case_count": len(cases), "figure_count": len(figures),
                    "source_files": {Path(__file__).name: _sha(Path(__file__)), Path(notebook).name: _sha(Path(notebook)),
                                     "synthetic_demo.py": _sha(Path(_network.__code__.co_filename))},
                    "files": {p.name: {"sha256": _sha(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
        write_json("metadata.json", metadata)
        return metadata
    except Exception as exc:
        write_json("failure.json", {"status": "failed", "error_type": type(exc).__name__, "message": str(exc)})
        raise
