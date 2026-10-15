"""Reproducible SNA diagnostics for a frozen training pilot.

CLI: python -m reddit_sna.reporting.validation --project . --detection-run ID
     --output-id ID [--sensitivity]

The sensitivity schedule is fixed before looking at scores. It evaluates the
original quarter, retains gamma=1 as canonical and never selects a best seed.
"""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version
import json
import math
from pathlib import Path
import random
import time
import sys

from reddit_sna.config import validate_run_id
from reddit_sna.data.archive import digest_file
from reddit_sna.data.normalize import open_readonly
from reddit_sna.detection.leiden import dependencies
from reddit_sna.graphs.audit import VALID_REPLY
from reddit_sna.graphs.provenance import ORDERED_GRAPH_PROTOCOL, ordered_nodes
from reddit_sna.reporting.handoff import inspect_handoff
from reddit_sna.reporting.pilot import load_pilot, read_csv

SCHEDULE = {"months": ["2015-01", "2015-02", "2015-03"], "gammas": [0.5, 1.0, 2.0],
            "detector_seeds": [0, 1, 2], "edge_drop_fraction": 0.05, "drop_seeds": [100, 101, 102]}
CONTEXTS = ("AskALiberal", "moderatepolitics", "PoliticalDiscussion")


def graph_from_rows(rows, users=(), *, node_order=None):
    """Build simple undirected weighted R, optionally retaining observed isolates."""
    ig, _ = dependencies()
    names = sorted(set(users) | {r[k] for r in rows for k in ("source_user_id", "target_user_id")})
    if node_order is not None:
        selected = set(names)
        names = [uid for uid in node_order if uid in selected]
        if len(names) != len(selected) or len(set(names)) != len(names):
            raise ValueError("Analysis node order does not uniquely cover graph users")
    index = {u: i for i, u in enumerate(names)}
    seen, edges, weights = set(), [], []
    for row in rows:
        u, v = row["source_user_id"], row["target_user_id"]
        pair, weight = tuple(sorted((u, v))), float(row["weight"])
        if u == v or pair in seen or not math.isfinite(weight) or weight <= 0:
            raise ValueError("Analysis requires unique non-self finite positive R edges")
        seen.add(pair); edges.append((index[u], index[v])); weights.append(weight)
    if node_order is not None:
        indexed = sorted((min(u,v),max(u,v),w) for (u,v),w in zip(edges,weights))
        edges, weights = [(u,v) for u,v,_ in indexed], [w for _,_,w in indexed]
    graph = ig.Graph(n=len(names), edges=edges, directed=False)
    graph.es["weight"] = weights
    return graph, names


def network_metrics(graph) -> dict:
    """Compute exact observed-union metrics, including degree-zero isolates.

    Strength is incident R weight, so its total is twice the reply-event weight.
    Top 1% share uses ceil(0.01*n) observed users and strength / total strength,
    not a fraction of unique events. Density is unweighted and loop-free.
    """
    n, e = graph.vcount(), graph.ecount()
    degrees = graph.degree()
    strengths = graph.strength(weights="weight")
    components = sorted(graph.connected_components().sizes(), reverse=True)
    top_n = math.ceil(n * .01)
    total_strength = sum(strengths)
    return {"observed_users": n, "edges": e, "components": len(components),
            "largest_component_users": components[0] if components else 0,
            "largest_component_fraction_observed": components[0]/n if n else None,
            "isolates": sum(d == 0 for d in degrees),
            "density_observed_union": 2*e/(n*(n-1)) if n > 1 else None,
            "degree_sum": sum(degrees), "strength_sum": total_strength,
            "mean_degree": sum(degrees)/n if n else None,
            "mean_strength": total_strength/n if n else None,
            "top_one_percent_users": top_n,
            "top_one_percent_strength_share": sum(sorted(strengths, reverse=True)[:top_n])/total_strength if total_strength else None,
            "degree_distribution": sorted(Counter(degrees).items()),
            "strength_distribution": sorted(Counter(strengths).items())}


def analyze_networks(pilot: dict) -> dict:
    """Return exact full-network and predeclared context diagnostics, no user IDs.

    Context R attributes an event to its child's corpus, with parent endpoints
    allowed elsewhere. Contexts overlap in users; this is not induced-subgraph
    ground truth or a counterfactual corpus-removal experiment.
    """
    monthly = []
    graphs = pilot["graphs"]
    with closing(open_readonly(pilot["runs"]["normalized"] / "normalized.sqlite")) as db:
        for summary in graphs["months"]:
            month = summary["month"]
            directory = pilot["runs"]["graphs"] / "snapshots" / month
            users = read_csv(directory / "users.csv")
            graph, _ = graph_from_rows(read_csv(directory / "R.csv"), (r["user_id"] for r in users))
            metrics = network_metrics(graph)
            if (metrics["observed_users"] != summary["observed_users"] or metrics["isolates"] != summary["isolates"]
                    or metrics["edges"] != summary["undirected_edges"]
                    or not math.isclose(metrics["strength_sum"], 2*summary["reply_events"])):
                raise ValueError("Graph analysis totals disagree with verified summary")
            cells = [r for r in graphs["corpus_month_audit"] if r["month"] == month]
            total = sum(r["valid_reply_events"] for r in cells)
            shares = {r["corpus"]: r["valid_reply_events"]/total if total else None for r in cells}
            contexts = {}
            for corpus in CONTEXTS:
                if corpus not in graphs["declared_corpora"]:
                    continue
                rows = db.execute(f"""SELECT MIN(c.user_id,p.user_id),MAX(c.user_id,p.user_id),COUNT(*)
                    FROM records c JOIN records p ON c.parent=p.id
                    WHERE c.month=? AND c.corpus=? AND c.kind='comment' AND {VALID_REPLY}
                    GROUP BY MIN(c.user_id,p.user_id),MAX(c.user_id,p.user_id)""", (month, corpus)).fetchall()
                edges = [{"source_user_id": u, "target_user_id": v, "weight": w} for u,v,w in rows]
                active = [r[0] for r in db.execute("SELECT DISTINCT user_id FROM records WHERE month=? AND corpus=? AND user_id IS NOT NULL", (month, corpus))]
                local, _ = graph_from_rows(edges, active)
                contexts[corpus] = network_metrics(local)
                expected = next(r["valid_reply_events"] for r in cells if r["corpus"] == corpus)
                if not math.isclose(contexts[corpus]["strength_sum"], 2*expected):
                    raise ValueError("Context analysis does not conserve attributed reply events")
            monthly.append({"month": month, **metrics, "corpus_event_shares": shares,
                            "corpus_share_hhi": sum(v*v for v in shares.values()) if total else None,
                            "zero_support_corpora": [r["corpus"] for r in cells if not r["records"]],
                            "predeclared_contexts": contexts})
    return {"population": "active authors union valid reply endpoints; includes isolates",
            "weight": "undirected R weight sums both reply directions; total strength double-counts events",
            "contexts": list(CONTEXTS), "context_policy": "child-corpus attributed replies; user sets overlap",
            "months": monthly}


def partition_comparison(left: dict, right: dict) -> dict:
    """Compare partitions on common users and expose endpoint attrition explicitly.

    Fewer than two common users, or constant partitions, have no informative ARI
    here. Undefined comparisons remain None rather than a perfect agreement.
    """
    ig, _ = dependencies()
    common = sorted(left.keys() & right.keys())
    a, b = [left[u] for u in common], [right[u] for u in common]
    def codes(labels):
        lookup = {label: i for i, label in enumerate(sorted(set(labels)))}
        return [lookup[label] for label in labels]
    meaningful = len(common) >= 2 and len(set(a)) > 1 and len(set(b)) > 1
    score = ig.compare_communities(codes(a), codes(b), method="adjusted_rand") if meaningful else None
    return {"common_users": len(common), "baseline_users": len(left), "candidate_users": len(right),
            "baseline_support_retained": len(common)/len(left) if left else None,
            "common_user_ARI": score if score is not None and math.isfinite(score) else None,
            "comparison_status": "informative" if meaningful else "insufficient_or_constant_partition"}


def sensitivity(pilot: dict, schedule=None) -> dict:
    """Run a predeclared quarter gamma/edge-drop diagnostic, never tune baseline.

    Drop floor(0.05 * unique undirected edges) uniformly without replacement;
    retained edge weights are unchanged. Detector seeds and drop seeds are
    distinct. Memberships are transient, only aggregate diagnostics are returned.
    """
    schedule = SCHEDULE if schedule is None else schedule
    ig, la = dependencies()
    if (not schedule["months"] or len(set(schedule["months"])) != len(schedule["months"])
            or not schedule["gammas"] or any(not math.isfinite(g) or g <= 0 for g in schedule["gammas"])
            or not 0 <= schedule["edge_drop_fraction"] < 1
            or not schedule["detector_seeds"] or len(set(schedule["detector_seeds"])) != len(schedule["detector_seeds"])):
        raise ValueError("Invalid sensitivity schedule")
    if not set(schedule["months"]).issubset(pilot["graphs"]["actual_months"]):
        raise ValueError("Sensitivity months must exist in the verified cohort")
    results = []
    for month in schedule["months"]:
        directory = pilot["runs"]["graphs"] / "snapshots" / month
        rows = read_csv(directory / "R.csv")
        order = None
        if pilot["graphs"].get("graph_protocol") == ORDERED_GRAPH_PROTOCOL:
            order = ordered_nodes(directory, {r[k] for r in rows for k in ("source_user_id","target_user_id")}, month)
        for seed in schedule["detector_seeds"]:
            relative = Path("memberships") / month / f"membership-seed{seed}.csv"
            hashes = {Path(p) for p in pilot["manifests"]["detection"]["artifact_hashes"]}
            if relative not in hashes:
                raise ValueError("Sensitivity seed membership missing from verified hash inventory")
            member_rows = read_csv(pilot["runs"]["detection"] / relative)
            result = next(m for m in pilot["detection"]["months"] if m["month"] == month)
            recorded = next(r for r in result["runs"] if r["seed"] == seed)
            baseline = {r["user_id"]: r["community_id"] for r in member_rows}
            endpoints = {r[k] for r in rows for k in ("source_user_id", "target_user_id")}
            if (len(baseline) != len(member_rows) or set(baseline) != endpoints
                    or any(r["month"] != month or r["reference_id"] != recorded["reference_id"] for r in member_rows)):
                raise ValueError("Sensitivity baseline membership key/reference/endpoint mismatch")
            for gamma, drop_seed in [(g, None) for g in schedule["gammas"]] + [(1.0, d) for d in schedule["drop_seeds"]]:
                count = math.floor(len(rows)*schedule["edge_drop_fraction"]) if drop_seed is not None else 0
                dropped = set(random.Random(drop_seed).sample(range(len(rows)), count)) if count else set()
                subset = [r for i,r in enumerate(rows) if i not in dropped]
                graph, names = graph_from_rows(subset, node_order=order)
                if names:
                    part = la.find_partition(graph, la.RBConfigurationVertexPartition, weights="weight",
                                             resolution_parameter=gamma, seed=seed, n_iterations=-1)
                    candidate = dict(zip(names, part.membership))
                    sizes = sorted(Counter(part.membership).values())
                    modularity = graph.modularity(part.membership, weights="weight")
                    connected = all(graph.subgraph(c).is_connected() for c in part)
                else:
                    candidate, sizes, modularity, connected = {}, [], None, None
                comparison = partition_comparison(baseline, candidate)
                baseline_replay_equal = None
                if gamma == 1 and drop_seed is None:
                    # Exact co-membership blocks, invariant to numeric cluster names.
                    def blocks(mapping):
                        groups = {}
                        for uid, label in mapping.items():
                            groups.setdefault(label, set()).add(uid)
                        return {frozenset(g) for g in groups.values()}
                    baseline_replay_equal = blocks(baseline) == blocks(candidate)
                results.append({"month": month, "gamma": gamma, "detector_seed": seed,
                                "drop_seed": drop_seed, "dropped_edges": count, "remaining_edges": len(subset),
                                "communities": len(sizes), "sizes": sizes, "modularity": modularity,
                                "all_communities_connected": connected,
                                "baseline_replay_partition_equal": baseline_replay_equal,
                                **comparison})
    return {"schedule": schedule, "baseline_unchanged": "gamma1 recorded memberships retained",
            "interpretation": "common-user ARI measures sensitivity; not social truth or independent replications",
            "runs": results}


def validate_pilot(project: Path, detection_run: str, output_id: str, *, run_sensitivity=False) -> Path:
    """Write a new provenance-linked validation run and retain failure state.

    The caller selects a recorded pilot explicitly. Expensive source integrity
    validation happens before reserving output. Runtime excludes this preflight;
    peak native memory is unmeasured and deliberately remains null.
    """
    validate_run_id(output_id)
    project = project.resolve()
    pilot = load_pilot(project, detection_run)
    root = (project / "artifacts").resolve()
    output = (root / "core" / output_id).resolve()
    if not output.is_relative_to(root):
        raise ValueError("Validation output must remain inside artifacts")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    manifest = {"status": "started", "created_at": datetime.now(timezone.utc).isoformat(),
                "source_runs": {k:str(v) for k,v in pilot["runs"].items()},
                "source_manifest_sha256": {k:digest_file(v / "manifest.json") for k,v in pilot["runs"].items()},
                "graph_reference": pilot["graphs"]["graph_reference"],
                "actual_months": pilot["graphs"]["actual_months"],
                "frozen_sensitivity_schedule": SCHEDULE if run_sensitivity else None,
                "predeclared_contexts": list(CONTEXTS),
                "dependencies": {k:version(k) for k in ("igraph","leidenalg","reddit-community-evolution")},
                "python": sys.version, "executable": sys.executable,
                "source_hashes": {str(p.relative_to(project)):digest_file(p) for p in sorted((project / "src/reddit_sna").rglob("*.py"))},
                "peak_memory_mb": None, "resource_note": "wall time excludes source validation; native peak memory not measured",
                "forecast_status": "not_implemented", "partner_acceptance": "not_verified"}
    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    save("manifest.json", manifest)
    try:
        save("handoff.json", inspect_handoff(pilot["runs"]["graphs"], pilot["runs"]["detection"], root))
        save("network_analysis.json", analyze_networks(pilot))
        if run_sensitivity:
            save("sensitivity.json", sensitivity(pilot))
        manifest["status"] = "complete"
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        manifest["wall_seconds"] = time.perf_counter()-started
        manifest["artifact_hashes"] = {p.name:digest_file(p) for p in output.iterdir() if p.is_file() and p.name != "manifest.json"}
        save("manifest.json", manifest)
    return output


def main():
    """Expose validation as an installed-package command, not a private task script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--detection-run", required=True)
    parser.add_argument("--output-id", required=True)
    parser.add_argument("--sensitivity", action="store_true")
    args = parser.parse_args()
    try:
        output = validate_pilot(args.project, args.detection_run, args.output_id, run_sensitivity=args.sensitivity)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Validation failed: {exc}\n")
    print(json.dumps({"validation_output":str(output), "forecast_status":"not_implemented"}))


if __name__ == "__main__":
    main()
