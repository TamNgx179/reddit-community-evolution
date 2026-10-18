"""Synthetic detection API; full tracking/evaluation pipeline remains unfinished."""

import csv
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, load_benchmark_config
from reddit_sna.benchmarks.io import read_edges, read_memberships, read_nodes, write_memberships
from reddit_sna.config import RunConfig, validate_run_id
from reddit_sna.detection.leiden import dependencies, detect_snapshots
from reddit_sna.pipelines import PipelineNotImplemented


def detect_synthetic_dataset(source: Path, output: Path) -> dict:
    """Detect one verified dataset at seed 0 / gamma 1 without reading truth.

    Read metadata/config and graph/node CSVs, never truth membership or labels.
    Parent of output must exist; output must be new and outside the source.
    Validate detector membership against exact R endpoints, then publish UTF-8
    LF CSVs in the new output folder. Return the detector diagnostics with
    synthetic provenance and active/isolate counts; persistence of the full
    dataset/reference mapping is a later adapter task.

    Temporary raw detector files retain the shared detector's original format.
    Only validated canonical memberships are written to the final directory.
    No tracker, AMI, seed selection by score or full-pipeline completion occurs.
    """
    source, output = source.resolve(), output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("detection output must not overlap its source dataset")
    if output.exists():
        raise FileExistsError(f"detection output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError("detection output parent must already exist")
    meta = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    if (type(meta.get("schema_version")) is not int or meta["schema_version"] != 1
            or meta.get("artifact_type") != "synthetic-graph-truth" or meta.get("status") != "complete"):
        raise ValueError("a complete synthetic graph dataset with schema 1 is required")
    dataset_id = validate_run_id(meta["dataset_id"])
    if meta["identity_scope"] != dataset_id:
        raise ValueError("dataset identity scope mismatch")
    months = meta["observed_months"]
    files = ["benchmark-config.json"]
    # Validate months before using their values as relative paths.
    benchmark_path = (source / "benchmark-config.json").resolve()
    if not benchmark_path.is_relative_to(source):
        raise ValueError("source config escapes dataset")
    expected_hash = meta["files"].get("benchmark-config.json", {}).get("sha256")
    if sha256(benchmark_path.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("source SHA-256 mismatch: benchmark-config.json")
    benchmark = load_benchmark_config(benchmark_path)
    if months != benchmark["months"]:
        raise ValueError("observed months must match the synthetic benchmark config")
    split, scenario, generator_seed = meta["split"], meta["scenario"], meta["generator_seed"]
    if (split not in ("development", "evaluation") or scenario not in benchmark["scenarios"]
            or type(generator_seed) is not int or generator_seed not in benchmark["generator"]["seeds"][split]
            or dataset_id != f"{'dev' if split == 'development' else 'eval'}-{scenario}-easy-g{generator_seed}"):
        raise ValueError("dataset ID must match its scenario and configured split/seed")
    if meta["graph"] != {"directed": False, "simple": True, "weight": 1.0}:
        raise ValueError("a simple undirected unit-weight synthetic graph is required")
    if benchmark["detector"]["gamma"] != 1 or benchmark["detector"]["canonical_seed"] != 0:
        raise ValueError("initial synthetic adapter requires gamma 1 and canonical seed 0")
    files.extend(f"snapshots/{month}/{name}.csv" for month in months for name in ("R", "nodes"))
    input_hashes = {}
    for name in files:
        path = (source / name).resolve()
        if not path.is_relative_to(source):
            raise ValueError("source graph file escapes dataset")
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != meta["files"].get(name, {}).get("sha256"):
            raise ValueError(f"source SHA-256 mismatch: {name}")
        input_hashes[name] = digest
    active, endpoints = {}, {}
    for month in months:
        folder = source / "snapshots" / month
        active[month] = read_nodes(folder / "nodes.csv", expected_month=month)
        edges = read_edges(folder / "R.csv", expected_month=month, expected_users=active[month])
        with (folder / "R.csv").open(encoding="utf-8", newline="") as handle:
            pairs = [(row["source_user_id"], row["target_user_id"]) for row in csv.DictReader(handle)]
        if pairs != sorted(pairs) or any(edge.weight != 1.0 for edge in edges):
            raise ValueError("synthetic edges must be sorted with weight 1.0")
        endpoints[month] = {uid for edge in edges for uid in (edge.source_user_id, edge.target_user_id)}
        if (len(active[month]) != meta["counts"]["nodes_by_month"][month]
                or len(edges) != meta["counts"]["edges_by_month"][month]):
            raise ValueError("source node/edge counts do not match metadata")
    dependencies()  # Explain optional dependency failure before any detector output.
    with TemporaryDirectory(prefix="synthetic-leiden-", dir=output.parent) as temporary:
        scratch = Path(temporary) / "memberships"
        result = detect_snapshots(
            source / "snapshots", scratch, meta["identity_scope"],
            seeds=(0,), gamma=1.0, graph_protocol=GRAPH_PROTOCOL, expected_months=months,
        )
        validated, references = {}, set()
        if (result["graph_protocol"] != GRAPH_PROTOCOL or result["actual_months"] != months
                or result["canonical_seed"] != 0 or result["gamma"] != 1.0
                or [row["month"] for row in result["months"]] != months):
            raise ValueError("detector returned a different synthetic cohort/config")
        for info in result["months"]:
            month = info["month"]
            if len(info["runs"]) != 1 or info["runs"][0]["seed"] != 0:
                raise ValueError("initial synthetic adapter requires exactly seed 0")
            run = info["runs"][0]
            reference = run["reference_id"]
            rows = read_memberships(scratch / month / "membership-seed0.csv",
                                    expected_reference=reference, expected_users_by_month={month: endpoints[month]})
            if (reference == meta["truth_reference"] or not reference.startswith(dataset_id + ":")
                    or run["assigned_users"] != len(endpoints[month])):
                raise ValueError("detector reference or endpoint count mismatch")
            references.add(reference)
            validated[month] = (reference, rows)
        if len(references) != 1:
            raise ValueError("one detector seed must share one reference across observed months")
        # Detect any source mutation before publishing the validated files.
        if any(sha256((source / name).read_bytes()).hexdigest() != digest for name, digest in input_hashes.items()):
            raise ValueError("source graph changed during detection")
        output.mkdir(exist_ok=False)
        for month, (reference, rows) in validated.items():
            (output / month).mkdir()
            write_memberships(output / month / "membership-seed0.csv", rows,
                              expected_reference=reference, expected_users_by_month={month: endpoints[month]})
    return {
        **result, "dataset_id": dataset_id, "identity_scope": meta["identity_scope"],
        "input_kind": "synthetic", "source_files": {name: {"sha256": digest} for name, digest in input_hashes.items()},
        "active_nodes_by_month": {month: len(users) for month, users in active.items()},
        "isolates_by_month": {month: len(set(active[month]) - endpoints[month]) for month in months},
        "membership_schema_version": 1, "membership_order": "month,community_id,user_id",
        "node_order_policy": "lexicographic synthetic user IDs and validated lexicographic edge insertion order",
        "notes": ["synthetic graph; planted labels are not detector input",
                  "isolated users not assigned; see source nodes.csv",
                  "initial seed 0 only; no cross-seed ARI or AMI ground-truth evaluation"],
    }


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "detection-tracking is scaffold-only: implement graph benchmark generation, "
        "detection, tracking and evaluation before running it"
    )
