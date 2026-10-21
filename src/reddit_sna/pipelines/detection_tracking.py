"""Synthetic detection and development benchmark APIs; tracking remains unfinished."""

from collections import Counter
import csv
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

from reddit_sna.artifacts import RunRecorder, capture_run_provenance, create_run_directory
from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset, read_edges, read_memberships, read_nodes, write_memberships
from reddit_sna.config import ConfigError, RunConfig, validate_destination, validate_run_id
from reddit_sna.contracts import PipelineName
from reddit_sna.detection.leiden import dependencies, detect_snapshots
from reddit_sna.pipelines import PipelineNotImplemented


def _check_detection_output(source: Path, output: Path) -> None:
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("detection output must not overlap its source dataset")
    if output.exists():
        raise FileExistsError(f"detection output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError("detection output parent must already exist")


def detect_synthetic_dataset(
    source: Path, output: Path, *, benchmark_config: Path | None = None,
) -> dict:
    """Detect one verified dataset using the fixed week-one detector schedule.

    Read metadata/config and graph/node CSVs, never truth membership or labels.
    An explicit benchmark_config selects the runtime detector configuration;
    otherwise use the source dataset's archived benchmark-config.json. Graph
    recipe fields must match the source. Week one requires seeds 0/1/2 in that
    order, gamma 1 and canonical 0; never select a seed by partition quality.
    Parent of output must exist; output must be new and outside the source.
    Validate detector membership against exact R endpoints, then publish UTF-8
    LF CSVs in the new output folder. Return the detector diagnostics with
    synthetic provenance and active/isolate counts. Use export_synthetic_detection
    to persist these diagnostics and a dataset/reference/file mapping together.

    Temporary raw detector files retain the shared detector's original format.
    Only validated canonical memberships are written to the final directory.
    No tracker, AMI, seed selection by score or full-pipeline completion occurs.
    """
    source, output = source.resolve(), output.resolve()
    _check_detection_output(source, output)
    metadata_bytes = (source / "metadata.json").read_bytes()
    meta = json.loads(metadata_bytes.decode("utf-8"))
    required = {"schema_version", "artifact_type", "status", "dataset_id", "identity_scope", "observed_months",
                "split", "scenario", "generator_seed", "truth_reference", "graph", "counts", "files"}
    if not isinstance(meta, dict) or not required.issubset(meta):
        raise ValueError("source metadata must be an object with all required graph dataset fields")
    if (type(meta.get("schema_version")) is not int or meta["schema_version"] != 1
            or meta.get("artifact_type") != "synthetic-graph-truth" or meta.get("status") != "complete"):
        raise ValueError("a complete synthetic graph dataset with schema 1 is required")
    dataset_id = validate_run_id(meta["dataset_id"])
    if meta["identity_scope"] != dataset_id:
        raise ValueError("dataset identity scope mismatch")
    if meta["truth_reference"] != f"truth-{dataset_id}":
        raise ValueError("source truth reference must match its dataset ID")
    if not isinstance(meta["files"], dict) or not isinstance(meta["counts"], dict):
        raise ValueError("source files and counts must be metadata objects")

    def expected_digest(name):
        info = meta["files"].get(name)
        if (not isinstance(info, dict) or not isinstance(info.get("sha256"), str)
                or len(info["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in info["sha256"])):
            raise ValueError(f"source metadata requires a SHA-256 for {name}")
        return info["sha256"]

    months = meta["observed_months"]
    files = ["benchmark-config.json"]
    # Validate months before using their values as relative paths.
    benchmark_path = (source / "benchmark-config.json").resolve()
    if not benchmark_path.is_relative_to(source):
        raise ValueError("source config escapes dataset")
    expected_hash = expected_digest("benchmark-config.json")
    if sha256(benchmark_path.read_bytes()).hexdigest() != expected_hash:
        raise ValueError("source SHA-256 mismatch: benchmark-config.json")
    benchmark = load_benchmark_config(benchmark_path)
    if months != benchmark["months"]:
        raise ValueError("observed months must match the synthetic benchmark config")
    for kind in ("nodes_by_month", "edges_by_month"):
        counts = meta["counts"].get(kind)
        if (not isinstance(counts, dict) or set(counts) != set(months)
                or any(type(n) is not int or n < 0 for n in counts.values())):
            raise ValueError(f"source {kind} must contain nonnegative integer counts for every observed month")
    split, scenario, generator_seed = meta["split"], meta["scenario"], meta["generator_seed"]
    if (split not in ("development", "evaluation") or scenario not in benchmark["scenarios"]
            or type(generator_seed) is not int or generator_seed not in benchmark["generator"]["seeds"][split]
            or dataset_id != f"{'dev' if split == 'development' else 'eval'}-{scenario}-{benchmark['difficulty']}-g{generator_seed}"):
        raise ValueError("dataset ID must match its scenario and configured split/seed")
    if meta["graph"] != {"directed": False, "simple": True, "weight": 1.0}:
        raise ValueError("a simple undirected unit-weight synthetic graph is required")
    detector_config_path = benchmark_config.resolve() if benchmark_config is not None else benchmark_path
    detector_config_hash = sha256(detector_config_path.read_bytes()).hexdigest()
    runtime = load_benchmark_config(detector_config_path)
    if ({key: value for key, value in runtime.items() if key != "detector"}
            != {key: value for key, value in benchmark.items() if key != "detector"}):
        raise ValueError("runtime graph recipe must match the source dataset config")
    detector = runtime["detector"]
    seeds, gamma, canonical = tuple(detector["seeds"]), float(detector["gamma"]), detector["canonical_seed"]
    if seeds != (0, 1, 2) or gamma != 1.0 or canonical != 0:
        raise ValueError("week-one detector requires seeds [0, 1, 2], gamma 1 and canonical seed 0")
    files.extend(f"snapshots/{month}/{name}.csv" for month in months for name in ("R", "nodes"))
    input_hashes = {"metadata.json": sha256(metadata_bytes).hexdigest()}
    for name in files:
        path = (source / name).resolve()
        if not path.is_relative_to(source):
            raise ValueError("source graph file escapes dataset")
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != expected_digest(name):
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
            seeds=seeds, gamma=gamma, graph_protocol=GRAPH_PROTOCOL, expected_months=months,
        )
        validated, references = {}, {seed: set() for seed in seeds}
        if (result["graph_protocol"] != GRAPH_PROTOCOL or result["actual_months"] != months
                or result["canonical_seed"] != canonical or result["gamma"] != gamma
                or [row["month"] for row in result["months"]] != months):
            raise ValueError("detector returned a different synthetic cohort/config")
        for info in result["months"]:
            month = info["month"]
            if (info["nodes_with_edges"] != len(endpoints[month])
                    or info["edges"] != meta["counts"]["edges_by_month"][month]):
                raise ValueError("detector graph counts do not match source endpoints/edges")
            stability = info["seed_pair_ARI"]
            if (not isinstance(stability, list) or len(stability) != (3 if endpoints[month] else 0)
                    or any(type(value) not in (int, float) or not math.isfinite(value)
                           or not -1 - 1e-12 <= value <= 1 + 1e-12 for value in stability)):
                raise ValueError("detector seed ARI must describe the three pairs, or be empty for an empty graph")
            if [run["seed"] for run in info["runs"]] != list(seeds):
                raise ValueError("detector runs must preserve the configured seed order")
            validated[month] = []
            for run in info["runs"]:
                seed, reference = run["seed"], run["reference_id"]
                rows = read_memberships(scratch / month / f"membership-seed{seed}.csv",
                                        expected_reference=reference, expected_users_by_month={month: endpoints[month]})
                if (reference == meta["truth_reference"]
                        or not reference.startswith(f"{dataset_id}:{result['graph_reference']}:")
                        or not reference.endswith(f"-gamma{gamma:g}-seed{seed}")
                        or run["assigned_users"] != len(endpoints[month])):
                    raise ValueError("detector reference or endpoint count mismatch")
                sizes = sorted(Counter(row.community_id for row in rows).values())
                if run["sizes"] != sizes or run["communities"] != len(sizes):
                    raise ValueError("detector community counts/sizes do not match membership CSV")
                quality = (run["modularity"], run["rb_objective"])
                if endpoints[month]:
                    if (run["status"] != "complete"
                            or any(type(value) not in (int, float) or not math.isfinite(value) for value in quality)):
                        raise ValueError("nonempty detector membership requires complete status and finite quality")
                elif (run["status"] != "empty_graph_no_partition" or any(value is not None for value in quality)
                      or run["all_communities_connected"] is not None):
                    raise ValueError("empty graph must have no partition quality or connectivity claim")
                references[seed].add(reference)
                validated[month].append((seed, reference, rows))
        if (any(len(refs) != 1 for refs in references.values())
                or len(set().union(*references.values())) != len(seeds)):
            raise ValueError("each seed needs one distinct reference shared across observed months")
        # Detect any source mutation before publishing the validated files.
        if any(sha256((source / name).read_bytes()).hexdigest() != digest for name, digest in input_hashes.items()):
            raise ValueError("source graph changed during detection")
        if sha256(detector_config_path.read_bytes()).hexdigest() != detector_config_hash:
            raise ValueError("runtime detector config changed during detection")
        output.mkdir(exist_ok=False)
        for month, runs in validated.items():
            (output / month).mkdir()
            for seed, reference, rows in runs:
                write_memberships(output / month / f"membership-seed{seed}.csv", rows,
                                  expected_reference=reference, expected_users_by_month={month: endpoints[month]})
    return {
        **result, "dataset_id": dataset_id, "identity_scope": meta["identity_scope"],
        "source_dataset": str(source), "split": split, "scenario": scenario,
        "generator_seed": generator_seed, "truth_reference": meta["truth_reference"],
        "input_kind": "synthetic", "source_files": {name: {"sha256": digest} for name, digest in input_hashes.items()},
        "active_nodes_by_month": {month: len(users) for month, users in active.items()},
        "isolates_by_month": {month: len(set(active[month]) - endpoints[month]) for month in months},
        "membership_schema_version": 1, "membership_order": "month,community_id,user_id",
        "detector_seeds": list(seeds),
        "detector_config": {"source": str(detector_config_path), "sha256": detector_config_hash,
                            "selection_policy": "configured first seed; no score selection"},
        "node_order_policy": "lexicographic synthetic user IDs and validated lexicographic edge insertion order",
        "notes": ["synthetic graph; planted labels are not detector input",
                  "isolated users not assigned; see source nodes.csv",
                  "seed-pair ARI measures repeatability, not AMI ground-truth accuracy",
                  "canonical seed is fixed to configured first seed 0, regardless of quality scores"],
    }


def _write_detection_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def export_synthetic_detection(
    source: Path, output: Path, *, benchmark_config: Path | None = None,
) -> dict:
    """Export one new detection dataset, returning its schema-1 metadata.

    Keep the membership-only API intact. Stage validated memberships, the full
    diagnostics dictionary and an exact runtime config copy before reserving
    output. Metadata maps each dataset/month/seed/reference to a relative CSV
    and its hash, including empty CSVs. Write complete metadata last; never
    overwrite an old output or modify source graph/truth metadata. This is only
    detection, not a full run manifest, community tracking or AMI evaluation.
    """
    source, output = source.resolve(), output.resolve()
    _check_detection_output(source, output)
    with TemporaryDirectory(prefix="synthetic-detection-export-", dir=output.parent) as temporary:
        stage = Path(temporary)
        diagnostics = detect_synthetic_dataset(source, stage / "memberships", benchmark_config=benchmark_config)
        config = diagnostics["detector_config"]
        config_bytes = Path(config["source"]).read_bytes()
        if sha256(config_bytes).hexdigest() != config["sha256"]:
            raise ValueError("runtime detector config changed before export")
        with (stage / "detector-config.json").open("xb") as handle:
            handle.write(config_bytes)
        _write_detection_json(stage / "detection.json", diagnostics)
        memberships = []
        for info in diagnostics["months"]:
            month = info["month"]
            for run in info["runs"]:
                name = f"memberships/{month}/membership-seed{run['seed']}.csv"
                memberships.append({
                    "dataset_id": diagnostics["dataset_id"], "identity_scope": diagnostics["identity_scope"],
                    "month": month, "seed": run["seed"], "reference_id": run["reference_id"],
                    "canonical": run["seed"] == diagnostics["canonical_seed"],
                    "path": name, "sha256": sha256((stage / name).read_bytes()).hexdigest(),
                    "graph_file": f"snapshots/{month}/R.csv", "nodes_file": f"snapshots/{month}/nodes.csv",
                    "graph_sha256": info["graph_sha256"], "status": run["status"],
                    "active_nodes": diagnostics["active_nodes_by_month"][month],
                    "assigned_users": run["assigned_users"], "isolates": diagnostics["isolates_by_month"][month],
                })
        metadata = {
            "schema_version": 1, "artifact_type": "synthetic-detection", "status": "complete",
            "scope": "detection", "completed_stages": ["detection"],
            "dataset_id": diagnostics["dataset_id"], "identity_scope": diagnostics["identity_scope"],
            "split": diagnostics["split"], "scenario": diagnostics["scenario"],
            "generator_seed": diagnostics["generator_seed"], "truth_reference": diagnostics["truth_reference"],
            "observed_months": diagnostics["actual_months"], "graph_protocol": diagnostics["graph_protocol"],
            "graph_reference": diagnostics["graph_reference"],
            "snapshot_cohort_sha256": diagnostics["snapshot_cohort_sha256"],
            "membership_schema_version": 1, "diagnostics_schema_version": diagnostics["schema_version"],
            "diagnostics_file": "detection.json", "memberships": memberships,
            "detector_references": {str(run["seed"]): run["reference_id"]
                                    for run in diagnostics["months"][0]["runs"]},
            "detector": {"seeds": diagnostics["detector_seeds"], "gamma": diagnostics["gamma"],
                         "canonical_seed": diagnostics["canonical_seed"], "config_file": "detector-config.json",
                         "config_sha256": config["sha256"], "selection_policy": config["selection_policy"],
                         "versions": diagnostics["versions"]},
            "source": {"directory": str(source), "files": diagnostics["source_files"]},
            "environment": {"python_version": platform.python_version(),
                            "package_version": version("reddit-community-evolution")},
            "files": {path.relative_to(stage).as_posix(): {"sha256": sha256(path.read_bytes()).hexdigest()}
                      for path in sorted(stage.rglob("*")) if path.is_file()},
        }
        # Recheck source provenance after preparing the package, before publishing.
        if any(sha256((source / name).read_bytes()).hexdigest() != item["sha256"]
               for name, item in diagnostics["source_files"].items()):
            raise ValueError("source graph or metadata changed before export")
        _write_detection_json(stage / "metadata.json", metadata)
        output.mkdir(exist_ok=False)
        for name in ("memberships", "detector-config.json", "detection.json", "metadata.json"):
            (stage / name).rename(output / name)
    return metadata


def run_synthetic_benchmark(
    config: RunConfig, *, protocol: Path, dataset_ids=None,
) -> Path:
    """Generate, detect and score a new development run, without a tracker.

    None selects the complete configured development schedule. An explicit
    nonempty dataset-ID subset retains protocol order. Evaluation IDs are
    rejected until the separate freeze/evaluation workflow is implemented.
    RunConfig.seed names the canonical detector seed, not a generator seed.
    Snapshot inputs before work; keep partial outputs and a failed manifest on
    errors. Scope is development-detection-evaluation, never full tracking.
    Record source/config/output hashes, runtime environment and scoped timings.
    Configuration snapshots are provenance; formal evaluation freeze is separate.
    """
    from importlib import import_module
    from reddit_sna.benchmarks.protocol import load_benchmark_protocol
    from reddit_sna.evaluation.detection import export_detection_evaluation

    preflight_started = perf_counter()
    if (config.pipeline != PipelineName.DETECTION_TRACKING or config.input_kind != "synthetic"
            or config.input_path is not None):
        raise ConfigError("synthetic benchmark requires detection-tracking, synthetic input and no input.path")
    validate_destination(config)
    plan = load_benchmark_protocol(protocol)
    if type(config.seed) is not int or config.seed != plan.benchmark["detector"]["canonical_seed"]:
        raise ConfigError("RunConfig.seed must equal canonical detector seed 0")
    schedule = dataset_schedule(plan.benchmark, "development")
    if dataset_ids is None:
        selected, mode = schedule, "full-development"
    else:
        if isinstance(dataset_ids, (str, bytes, Path)):
            raise ConfigError("dataset_ids must be a nonempty iterable of development IDs")
        try:
            requested = tuple(dataset_ids)
        except TypeError as exc:
            raise ConfigError("dataset_ids must be a nonempty iterable of development IDs") from exc
        if (not requested or any(not isinstance(name, str) for name in requested)
                or len(set(requested)) != len(requested)
                or not set(requested) <= {row["dataset_id"] for row in schedule}):
            raise ConfigError("select unique configured development dataset IDs; evaluation is not enabled")
        selected = tuple(row for row in schedule if row["dataset_id"] in set(requested))
        mode = "development-subset"
    protocol_bytes, recipe_bytes, run_config_bytes = (path.read_bytes() for path in
        (plan.protocol_path, plan.benchmark_path, config.source))
    if (sha256(protocol_bytes).hexdigest() != plan.protocol_sha256
            or sha256(recipe_bytes).hexdigest() != plan.benchmark_sha256):
        raise ConfigError("protocol or benchmark changed during preflight")
    dependencies()
    try:
        import_module("sklearn.metrics")
    except ModuleNotFoundError as exc:
        if exc.name in ("sklearn", "sklearn.metrics"):
            raise ImportError("install benchmark dependencies with pip install -e '.[graph,evaluation]'") from exc
        raise
    source, environment, source_bytes = capture_run_provenance()
    preflight_seconds = perf_counter() - preflight_started
    run = create_run_directory(config)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    expected = {"datasets": len(selected), "snapshots": len(selected) * len(plan.benchmark["months"]),
                "snapshot_detector_runs": len(selected) * len(plan.benchmark["months"]) * len(plan.benchmark["detector"]["seeds"])}
    manifest.update(schema_version=2, artifact_type="synthetic-detection-evaluation-run",
                    scope="development-detection-evaluation", split="development",
                    selection={"mode": mode, "dataset_ids": [row["dataset_id"] for row in selected]},
                    expected_counts=expected, completed_stages=[], current_stage="configuration", current_dataset=None,
                    generated_datasets=[], detected_datasets=[], tracking_status="not_implemented",
                    freeze_record_created=False,
                    source=source, environment=environment, preflight_wall_seconds=preflight_seconds,
                    preflight_scope="config/selection/backend checks and provenance capture before run reservation",
                    config_inputs={
                        "protocol": {"source": str(plan.protocol_path), "archive": "config/protocol/" + plan.protocol_path.name,
                                     "sha256": plan.protocol_sha256},
                        "benchmark": {"source": str(plan.benchmark_path), "archive": "config/protocol/" + plan.benchmark_path.name,
                                      "sha256": plan.benchmark_sha256},
                        "run_config": {"source": str(config.source), "archive": "config/run-config.toml",
                                       "sha256": sha256(run_config_bytes).hexdigest()}},
                    dataset_records={item["dataset_id"]: {**item, **{
                        stage: {"status": "pending", "wall_seconds": None} for stage in ("generation", "detection", "evaluation")}}
                        for item in selected},
                    protocol={"source": str(plan.protocol_path), "sha256": plan.protocol_sha256,
                              "benchmark_sha256": plan.benchmark_sha256})
    recorder = RunRecorder(run, manifest)
    try:
        with recorder.stage("configuration"):
            archived = run / "config" / "protocol"
            archived.mkdir(parents=True)
            (archived / plan.protocol_path.name).write_bytes(protocol_bytes)
            (archived / plan.benchmark_path.name).write_bytes(recipe_bytes)
            (run / "config/run-config.toml").write_bytes(run_config_bytes)
            _write_detection_json(run / "config/resolved-run-config.json", config.to_dict())
            manifest["resolved_config"] = {"archive": "config/resolved-run-config.json",
                "sha256": sha256((run / "config/resolved-run-config.json").read_bytes()).hexdigest()}
            for name, data in source_bytes.items():
                target = run / source["archive_root"] / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            _write_detection_json(run / "provenance/environment.json", environment)
            _write_detection_json(run / "provenance/source.json", source)
            archived_plan = load_benchmark_protocol(archived / plan.protocol_path.name)
            source_root, detected_root = run / "inputs/source", run / "inputs/detected"
            source_root.mkdir(parents=True)
            detected_root.mkdir()
        with recorder.stage("generation"):
            for item in selected:
                dataset = item["dataset_id"]
                with recorder.dataset("generation", dataset) as record:
                    export_graph_dataset(source_root / dataset, benchmark=archived_plan.benchmark,
                                         scenario=item["scenario"], generator_seed=item["generator_seed"], split="development")
                    record["metadata"] = f"inputs/source/{dataset}/metadata.json"
                    manifest["generated_datasets"].append(dataset)
        with recorder.stage("detection"):
            for item in selected:
                dataset = item["dataset_id"]
                with recorder.dataset("detection", dataset) as record:
                    export_synthetic_detection(source_root / dataset, detected_root / dataset,
                                               benchmark_config=archived_plan.benchmark_path)
                    record["metadata"] = f"inputs/detected/{dataset}/metadata.json"
                    manifest["detected_datasets"].append(dataset)
        with recorder.stage("evaluation"):
            report = export_detection_evaluation(
                [(source_root / item["dataset_id"], detected_root / item["dataset_id"]) for item in selected], run / "evaluation")
            actual = {"datasets": report["dataset_count"],
                      "snapshots": report["metric_rows"] // len(plan.benchmark["detector"]["seeds"]),
                      "snapshot_detector_runs": report["metric_rows"]}
            if actual != expected:
                raise ValueError("completed report counts differ from the selected development schedule")
            if (plan.protocol_path.read_bytes() != protocol_bytes or plan.benchmark_path.read_bytes() != recipe_bytes
                    or config.source.read_bytes() != run_config_bytes):
                raise ValueError("source configuration changed during the benchmark run")
            manifest.update(actual_counts=actual, evaluation_directory="evaluation")
        recorder.complete()
    except BaseException as exc:
        recorder.fail(exc)
        raise
    return run


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "full detection-tracking is scaffold-only; use run_synthetic_benchmark for "
        "development detection evaluation; community tracking is not implemented"
    )


def main(argv=None):
    """Separate development command; the shared full-pipeline run stays explicit."""
    import argparse
    from reddit_sna.config import load_config
    parser = argparse.ArgumentParser(description="Run synthetic development generation, Leiden and detection evaluation.")
    parser.add_argument("--config", type=Path, default=Path("configs/detection_development.toml"))
    parser.add_argument("--protocol", type=Path, default=Path("configs/benchmark_week1_protocol.json"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-id", action="append", help="Development subset; default all configured development IDs")
    args = parser.parse_args(argv)
    try:
        output = run_synthetic_benchmark(load_config(args.config, run_id=args.run_id),
                                         protocol=args.protocol, dataset_ids=args.dataset_id)
    except (ValueError, OSError, ImportError) as exc:
        print(f"synthetic benchmark failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "complete", "scope": "development-detection-evaluation",
                      "run_directory": str(output), "tracking_status": "not_implemented",
                      "freeze_record_created": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
