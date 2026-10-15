"""Descriptive pilot figures: audited counts, coverage and partition diagnostics.

No figure estimates forecasting accuracy or treats subreddits as ground truth.
Plotting dependencies are optional and loaded only when figures are requested.
"""

from collections import Counter
from importlib.metadata import version
import json
import math
from pathlib import Path
import random

from reddit_sna.data.archive import digest_file
from reddit_sna.graphs.audit import OUTCOMES
from reddit_sna.reporting.pilot import read_csv


def plotting_dependencies():
    """Fail with setup guidance while leaving base CLI imports dependency-free."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Plotting dependencies missing. Install with the selected kernel's Python: "
            'python -m pip install -e ".[graph,notebook]"; then restart the kernel.'
        ) from exc
    return plt, np


def corpus_matrix(graphs: dict) -> tuple[list[str], list[str], list[list[int]]]:
    """Keep the declared corpus order and explicit zero-support corpus-months."""
    corpora, months = graphs["declared_corpora"], graphs["actual_months"]
    lookup = {(r["corpus"], r["month"]): r["records"] for r in graphs["corpus_month_audit"]}
    return corpora, months, [[lookup[c, m] for m in months] for c in corpora]


def sample_network(pilot: dict, *, limit: int = 150, seed: int = 42) -> dict:
    """Select the largest component of the first month's R, then a BFS sample.

    Sorted adjacency and a seeded start make selection repeatable. This connected
    display sample favors nearby nodes and is unsuitable for estimating metrics.
    Full-graph memberships and statistics remain independent of this sampling.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError("Network display limit must be a positive integer")
    month = pilot["graphs"]["actual_months"][0]
    edges = read_csv(pilot["runs"]["graphs"] / "snapshots" / month / "R.csv")
    adjacency = {}
    for row in edges:
        u, v = row["source_user_id"], row["target_user_id"]
        adjacency.setdefault(u, set()).add(v)
        adjacency.setdefault(v, set()).add(u)
    remaining, components = set(adjacency), []
    while remaining:
        todo, component = [min(remaining)], set()
        while todo:
            u = todo.pop()
            if u in component:
                continue
            component.add(u)
            todo.extend(sorted(adjacency[u] - component, reverse=True))
        remaining -= component
        components.append(component)
    largest = min(components, key=lambda c: (-len(c), min(c))) if components else set()
    chosen = []
    if largest:
        queue = [random.Random(seed).choice(sorted(largest))]
        seen = set(queue)
        for u in queue:
            chosen.append(u)
            if len(chosen) >= limit:
                break
            for v in sorted(adjacency[u]):
                if v not in seen:
                    seen.add(v)
                    queue.append(v)
    nodes = sorted(chosen)
    selected = set(nodes)
    return {"month": month, "nodes": nodes, "edges": [r for r in edges
            if r["source_user_id"] in selected and r["target_user_id"] in selected],
            "policy": "seeded BFS in largest component; induced edges; display only",
            "seed": seed, "limit": limit, "full_nodes": len(adjacency)}


def build_figures(pilot: dict, *, sample_limit=150, seed=42) -> dict:
    """Return eight named Matplotlib figures from verified ``load_pilot`` data.

    Counts use independent panels when units differ. Missing quality/coverage is
    represented by NaN (a gap), not zero. Caller owns display and figure closing.
    """
    plt, np = plotting_dependencies()
    from matplotlib.collections import LineCollection
    graphs, detection = pilot["graphs"], pilot["detection"]
    months, monthly = graphs["actual_months"], graphs["months"]
    canonical = [next(r for r in d["runs"] if r["seed"] == detection["canonical_seed"])
                 for d in detection["months"]]
    palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#666666"]
    figures = {}

    # Each bar states its own population: history is retained metadata, not loss.
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    counts = pilot["normalization"]["counts"]
    totals = [counts["raw_rows"], counts.get("inserted", 0),
              sum(graphs["historical_metadata_before_start"].values()),
              sum(r["records"] for r in graphs["corpus_month_audit"])]
    labels = ["Raw rows scanned", "Retained before cutoff", "Retained before pilot", "Records within pilot"]
    bars = ax.barh(labels, totals, color=palette[:4])
    ax.set_xscale("symlog", linthresh=1)
    ax.bar_label(bars, labels=[f"{v:,}" for v in totals], padding=4, fontsize=9)
    ax.set_xlim(0, max(totals + [1]) * 12)
    ax.set(xlabel="Records (symlog scale; populations overlap)", title="Data scope and observation cutoff")
    figures["01_data_scope"] = fig

    corpora, _, values = corpus_matrix(graphs)
    fig, ax = plt.subplots(figsize=(max(9, len(months)*1.1+3), max(4, len(corpora) * .32)), layout="constrained")
    image = ax.imshow(np.log1p(values), aspect="auto", cmap="cividis", vmin=0)
    ax.set_xticks(range(len(months)), months)
    ax.set_yticks(range(len(corpora)), corpora)
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value:,}", ha="center", va="center", fontsize=8,
                    color="white" if math.log1p(value) < image.norm.vmax * .55 else "black")
    fig.colorbar(image, ax=ax, label="log(1 + observed records)")
    ax.set_title("Corpus-month support: 0 means no observed activity")
    figures["02_corpus_support"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for key, label, color in (("active_authors", "Active authors", palette[0]),
                               ("reply_endpoints", "Reply endpoints", palette[2]),
                               ("isolates", "Observed isolates", palette[1])):
        axes[0].plot(months, [r[key] for r in monthly], "o-", label=label, color=color)
    for key, label, color in (("undirected_edges", "Unique undirected edges", palette[0]),
                               ("reply_events", "Directed reply events", palette[1])):
        axes[1].plot(months, [r[key] for r in monthly], "o-", label=label, color=color)
    for ax, label in zip(axes, ("Users", "Edges / events (different counts)")):
        ax.set(ylabel=label, ylim=(0, None)); ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle("Monthly graph volume (full graphs)")
    figures["03_graph_volume"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for key, label, color in (("reply_coverage_active_authors", "Covered active / active", palette[0]),
                               ("reply_coverage_observed_users", "Endpoints / observed union", palette[1])):
        axes[0].plot(months, [np.nan if r[key] is None else r[key] * 100 for r in monthly],
                     "o-", label=label, color=color)
    axes[0].set(ylabel="Coverage (%)", ylim=(0, 100)); axes[0].legend(fontsize=8)
    for key, label, color in (("isolates", "Isolates", palette[0]),
                               ("parent_only_endpoints", "Parent-only endpoints", palette[1])):
        axes[1].plot(months, [r[key] for r in monthly], "o-", label=label, color=color)
    axes[1].set(ylabel="Users", ylim=(0, None)); axes[1].legend(fontsize=8)
    fig.suptitle("Coverage denominators and excluded graph populations")
    figures["04_coverage"] = fig

    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    bottom = np.zeros(len(months))
    for outcome, color in zip(OUTCOMES, palette):
        values = [sum(r["reply_outcomes"][outcome] for r in graphs["corpus_month_audit"]
                      if r["month"] == m) for m in months]
        ax.bar(months, values, bottom=bottom, label=outcome.replace("_", " "), color=color)
        bottom += values
    ax.set(ylabel="Comments (one outcome per comment)", title="Reply audit: mutually exclusive outcomes")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    figures["05_reply_outcomes"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for month, run, color in zip(months, canonical, (palette * len(months))):
        sizes = sorted(run["sizes"])
        if sizes:
            axes[0].step(sizes, np.arange(1, len(sizes)+1)/len(sizes), where="post", label=month, color=color)
        axes[1].bar(month, run["communities"], color=color)
    axes[0].set(xscale="log", xlabel="Community size (users; log scale)", ylabel="Empirical cumulative fraction", ylim=(0, 1.02))
    if any(r["sizes"] for r in canonical):
        axes[0].legend()
    axes[1].set(ylabel="Communities", title=f"Canonical seed {detection['canonical_seed']}")
    fig.suptitle("Full-graph community size distribution; empty partitions omitted")
    figures["06_community_sizes"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    axes[0].plot(months, [np.nan if r["modularity"] is None else r["modularity"] for r in canonical], "o-", color=palette[0])
    axes[0].set(ylabel="Weighted modularity", ylim=(-.5, 1), title=f"RB resolution gamma = {detection['gamma']:g}")
    for i, result in enumerate(detection["months"]):
        stability = result["seed_pair_ARI"]
        axes[1].scatter([i]*len(stability), stability, color=palette[2], alpha=.7)
    axes[1].set_xticks(range(len(months)), months)
    axes[1].set(ylabel="Adjusted Rand index between seeds", ylim=(-1, 1.02), title="Repeatability; pairs are not independent tests")
    fig.suptitle("Partition diagnostics: neither panel measures social accuracy")
    figures["07_partition_diagnostics"] = fig

    sample = sample_network(pilot, limit=sample_limit, seed=seed)
    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    if sample["nodes"]:
        import igraph as ig
        index = {uid: i for i, uid in enumerate(sample["nodes"])}
        edges = [(index[r["source_user_id"]], index[r["target_user_id"]]) for r in sample["edges"]]
        graph = ig.Graph(n=len(index), edges=edges, directed=False)
        # Deterministic starting coordinates; layout is display-only and unweighted.
        rng = random.Random(seed)
        coords = np.array(graph.layout_fruchterman_reingold(seed=[[rng.random(), rng.random()] for _ in index], niter=200).coords)
        canonical_seed = detection["canonical_seed"]
        membership = read_csv(pilot["runs"]["detection"] / "memberships" / sample["month"] / f"membership-seed{canonical_seed}.csv")
        labels = {r["user_id"]: r["community_id"] for r in membership}
        classes = {label: i for i, label in enumerate(sorted(set(labels.values())))}
        colors = [classes[labels[uid]] for uid in sample["nodes"]]
        ax.add_collection(LineCollection([(coords[u], coords[v]) for u, v in edges], colors="#999999", linewidths=.4, alpha=.35))
        ax.scatter(coords[:, 0], coords[:, 1], c=colors, cmap="tab20", s=18, edgecolors="white", linewidths=.3)
        ax.autoscale_view()
        caption = f"{len(index)} / {sample['full_nodes']:,} endpoint users; induced edges; no user labels"
    else:
        caption = "Empty graph: no network or partition to display"
        ax.text(.5, .5, caption, ha="center", transform=ax.transAxes)
    ax.set_title(f"{sample['month']}: biased BFS display sample\nColors = full-graph communities (palette may repeat)", fontsize=10)
    ax.set_xlabel(caption, fontsize=8); ax.set_xticks([]); ax.set_yticks([])
    figures["08_network_sample"] = fig
    # Twelve-month figures need more horizontal space than the original quarter.
    if len(months) > 6:
        for name in ("03_graph_volume", "04_coverage", "05_reply_outcomes", "06_community_sizes", "07_partition_diagnostics"):
            figures[name].set_figwidth(15)
            for axis in figures[name].axes:
                if axis.get_xscale() == "linear":
                    axis.tick_params(axis="x", labelrotation=45)
    return figures


def export_figures(figures: dict, output: Path, pilot: dict, *, sample_limit=150, seed=42,
                   validation_runs=()) -> Path:
    """Reserve a new output directory and export figures plus source provenance.

    A started/failed manifest remains if export fails. Existing results are never
    overwritten. The notebook passes the same sampling parameters used for plots.
    """
    if not output.resolve().is_relative_to(pilot["runs"]["detection"].parents[1]):
        raise ValueError("Figure output must stay inside project artifacts")
    # Additional figures may combine annual analysis and a separately referenced
    # quarter sensitivity study. Preserve both sources without conflating cohorts.
    from reddit_sna.reporting.pilot import verified_manifest
    validation_sources = {}
    for run in validation_runs:
        verified_manifest(run, pilot["runs"]["detection"].parents[1])
        validation_sources[str(run)] = digest_file(run / "manifest.json")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "started", "source_runs": {k: str(v) for k, v in pilot["runs"].items()},
                "source_manifest_sha256": {k: digest_file(v / "manifest.json") for k, v in pilot["runs"].items()},
                "validation_manifest_sha256": validation_sources,
                "graph_reference": pilot["graphs"]["graph_reference"], "canonical_seed": pilot["detection"]["canonical_seed"],
                "plotting": {name: version(name) for name in ("matplotlib", "numpy", "igraph")},
                "source_sha256": {p.name: digest_file(p) for p in Path(__file__).parent.glob("*.py")},
                "sample": {"limit": sample_limit, "seed": seed, "policy": "seeded BFS in largest component; display only"},
                "interpretation": "descriptive data-to-membership diagnostics; no forecast evaluation"}
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        for name, fig in figures.items():
            if not name.replace("_", "").isalnum():
                raise ValueError("Unsafe figure name")
            for suffix in ("png", "svg"):
                fig.savefig(output / f"{name}.{suffix}", dpi=180, bbox_inches="tight")
        manifest["status"] = "complete"
    except BaseException:
        manifest["status"] = "failed"
        raise
    finally:
        manifest["artifact_hashes"] = {p.name: digest_file(p) for p in output.iterdir() if p.suffix in {".png", ".svg"}}
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output
