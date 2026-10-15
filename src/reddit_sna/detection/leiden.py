"""Independent Leiden on current-month R; no future graph or external team output."""

from collections import Counter
import csv
from importlib.metadata import version
import itertools
import math
from pathlib import Path
import time

from reddit_sna.graphs.snapshots import write_csv
from reddit_sna.graphs.provenance import GRAPH_PROTOCOL, ORDERED_GRAPH_PROTOCOL, ordered_nodes, snapshot_inventory


def dependencies():
    """Load optional graph libraries only when detection is requested; explain setup failures."""
    try:
        import igraph
        import leidenalg
    except ImportError as exc:
        raise ValueError("Leiden dependencies missing; install the project with [graph]") from exc
    return igraph, leidenalg


def detect_snapshots(snapshot_dir: Path, output: Path, identity_scope: str,
                     seeds=(0, 1, 2), gamma=1.0, *, graph_protocol=GRAPH_PROTOCOL, expected_months=None) -> dict:
    """Run independent weighted RBConfiguration Leiden on each verified month.

    Converge separately for every specified seed and positive gamma. The first
    seed is the canonical handoff, never the highest-scoring seed. Empty graphs
    produce no fabricated partition quality. Record sizes, connectivity and
    pairwise seed ARI as repeatability diagnostics, not ground-truth accuracy."""
    ig, la = dependencies()
    if not seeds or len(set(seeds)) != len(seeds) or not math.isfinite(gamma) or gamma <= 0:
        raise ValueError("unique seeds and positive resolution are required")
    inventory = snapshot_inventory(snapshot_dir, protocol=graph_protocol, expected_months=expected_months)
    output.mkdir(exist_ok=False)
    results = []
    for graph_info in inventory["month_graphs"]:
        month_path = snapshot_dir / graph_info["month"]
        started = time.perf_counter()
        with (month_path / "R.csv").open(encoding="utf-8", newline="") as handle:
            edges = list(csv.DictReader(handle))
        names = sorted({row[field] for row in edges for field in ("source_user_id", "target_user_id")})
        if graph_protocol == ORDERED_GRAPH_PROTOCOL:
            names = ordered_nodes(month_path, set(names), month_path.name)
        index = {uid: i for i, uid in enumerate(names)}
        indexed = [(min(index[r["source_user_id"]],index[r["target_user_id"]]),
                    max(index[r["source_user_id"]],index[r["target_user_id"]]),float(r["weight"])) for r in edges]
        if graph_protocol == ORDERED_GRAPH_PROTOCOL:
            indexed.sort()  # Canonical adjacency insertion order as well as vertices.
        graph = ig.Graph(n=len(names), edges=[(u,v) for u,v,_ in indexed], directed=False)
        weights = [w for _,_,w in indexed]
        if any(graph.is_loop()) or any(graph.is_multiple()) or any(not math.isfinite(w) or w <= 0 for w in weights):
            raise ValueError("R must have unique non-self edges with finite positive weights")
        month_out = output / month_path.name
        month_out.mkdir()
        partitions, runs = [], []
        for seed in seeds:
            reference = f"{identity_scope}:{inventory['graph_reference']}:leiden-rb-v2-gamma{gamma:g}-seed{seed}"
            if names:
                partition = la.find_partition(graph, la.RBConfigurationVertexPartition, weights=weights,
                                              resolution_parameter=gamma, n_iterations=-1, seed=seed)
                labels = partition.membership
                sizes = Counter(labels)
                modularity = graph.modularity(labels, weights=weights)
                objective = partition.quality()
                connected = all(graph.subgraph(cluster).is_connected() for cluster in partition)
            else:
                labels, sizes, modularity, objective, connected = [], Counter(), None, None, None
            write_csv(month_out / f"membership-seed{seed}.csv",
                      ["reference_id", "month", "community_id", "user_id"],
                      ((reference, month_path.name, f"c{label}", uid) for uid, label in zip(names, labels)))
            partitions.append(labels)
            runs.append({"seed": seed, "reference_id": reference, "assigned_users": len(names),
                         "communities": len(sizes), "sizes": sorted(sizes.values()),
                         "modularity": modularity, "rb_objective": objective,
                         "all_communities_connected": connected,
                         "status": "complete" if names else "empty_graph_no_partition"})
        # ARI between seeds is stability, not accuracy against social ground truth.
        stability = [ig.compare_communities(a, b, method="adjusted_rand")
                     for a, b in itertools.combinations(partitions, 2)] if names else []
        results.append({"month": month_path.name, "nodes_with_edges": len(names), "edges": len(edges),
                        "graph_sha256": graph_info["graph_sha256"],
                        "wall_seconds": time.perf_counter()-started,
                        "seed_pair_ARI": stability, "runs": runs})
    return {"status": "complete", "schema_version": 2, **inventory,
            "objective": "RBConfigurationVertexPartition", "gamma": gamma,
            "iterations": "until no improvement", "canonical_seed": seeds[0],
            "node_order_policy": "causal anchor and canonical edge indices" if graph_protocol == ORDERED_GRAPH_PROTOCOL else "legacy ordinal IDs; cross-run ordering invariance not guaranteed",
            "versions": {"igraph": version("igraph"), "leidenalg": version("leidenalg")},
            "months": results, "forecast_evaluation": "not implemented; handoff to tracking/features pipeline",
            "notes": ["no social ground truth on Reddit", "isolated users not assigned; see users.csv",
                      "seed ARI measures repeatability, not validity"]}
