"""Verify synthetic truth/detector inputs and align labels by user ID.

Align labels, count coverage, score AMI and export auditable evaluation reports.
Community names are preserved; aligning users is not community matching.
"""

from collections.abc import Iterable, Mapping
from collections import Counter
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from math import isfinite
from pathlib import Path
import platform
from statistics import fmean
from time import perf_counter
from types import MappingProxyType

from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.io import read_edges, read_memberships, read_nodes, validate_memberships
from reddit_sna.config import validate_run_id
from reddit_sna.contracts import Membership, next_month
from reddit_sna.graphs.provenance import snapshot_inventory


AMI_POLICY = MappingProxyType({
    "schema_version": 1,
    "policy_id": "synthetic-ami-v1",
    "library": "scikit-learn",
    "metric": "adjusted_mutual_info_score",
    "average_method": "arithmetic",
    "scoring_users": "verified_R_endpoints",
    "minimum_scored_users": 2,
    "empty_scored": "null:empty_scored",
    "insufficient_users": "null:insufficient_users",
    "constant_partition": "null:degenerate_partition",
    "all_singletons_partition": "null:degenerate_partition",
    "invalid_input": "raise",
    "nonfinite_score": "raise",
    "negative_scores": "preserve",
    "quality_summary_eligibility": "ami_status=ok",
})

SUMMARY_POLICY = MappingProxyType({
    "aggregation_unit": "dataset-month separately per detector seed",
    "ami_aggregation": "unweighted mean of rows with ami_status=ok",
    "coverage_aggregation": "unweighted mean of rows with defined coverage",
    "canonical_seed": 0,
    "pool_detector_seeds": False,
    "missing_ami": "exclude from mean; retain support, status and combined reason counts",
    "user_support": "user observations across rows, not distinct people",
})


@dataclass(frozen=True)
class AlignedSnapshot:
    month: str
    active_user_ids: tuple[str, ...]
    truth_labels_all: tuple[str, ...]
    user_ids: tuple[str, ...]
    truth_labels: tuple[str, ...]
    predicted_labels: tuple[str, ...]


@dataclass(frozen=True)
class AlignedDetection:
    dataset_id: str
    identity_scope: str
    split: str
    scenario: str
    difficulty: str
    generator_seed: int
    detector_seed: int
    gamma: float
    truth_reference: str
    detector_reference: str
    snapshots: tuple[AlignedSnapshot, ...]


@dataclass(frozen=True)
class DetectionCounts:
    month: str
    active_nodes: int
    endpoint_nodes: int
    assigned_nodes: int
    isolated_nodes: int
    coverage: float | None
    coverage_status: str
    true_communities_all_nodes: int
    true_communities_scored_nodes: int
    predicted_communities: int


@dataclass(frozen=True)
class DetectionAMI:
    month: str
    n_scored_users: int
    ami: float | None
    ami_status: str
    ami_reason: str | None
    ami_policy_id: str
    ami_average_method: str


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def count_snapshot(snapshot: AlignedSnapshot) -> DetectionCounts:
    """Count one verified frame; coverage uses all active users, not endpoints.

    A positive active population with no edges has coverage 0. Empty active
    populations have coverage None and status no_active_users. Group counts
    remain defined for empty/constant partitions; this function does not score
    partition quality or combine different months/seeds into independent units.
    """
    _require(isinstance(snapshot, AlignedSnapshot), "an AlignedSnapshot is required")
    next_month(snapshot.month)
    for users in (snapshot.active_user_ids, snapshot.user_ids):
        _require(isinstance(users, tuple) and all(isinstance(user, str) and user.strip() for user in users),
                 "aligned user IDs must be tuples of nonempty strings")
        _require(users == tuple(sorted(set(users))), "aligned user IDs must be sorted and unique")
    for labels in (snapshot.truth_labels_all, snapshot.truth_labels, snapshot.predicted_labels):
        _require(isinstance(labels, tuple) and all(isinstance(label, str) and label.strip() for label in labels),
                 "aligned labels must be tuples of nonempty strings")
    _require(len(snapshot.active_user_ids) == len(snapshot.truth_labels_all)
             and len(snapshot.user_ids) == len(snapshot.truth_labels) == len(snapshot.predicted_labels),
             "aligned user/label vector lengths must match")
    active_truth = dict(zip(snapshot.active_user_ids, snapshot.truth_labels_all, strict=True))
    _require(set(snapshot.user_ids) <= active_truth.keys(), "scored user is outside active users")
    _require(snapshot.truth_labels == tuple(active_truth[user] for user in snapshot.user_ids),
             "scored truth must match all-active truth by user ID")
    active, endpoints, assigned = len(snapshot.active_user_ids), len(snapshot.user_ids), len(snapshot.predicted_labels)
    return DetectionCounts(
        month=snapshot.month, active_nodes=active, endpoint_nodes=endpoints, assigned_nodes=assigned,
        isolated_nodes=active - endpoints, coverage=assigned / active if active else None,
        coverage_status="defined" if active else "no_active_users",
        true_communities_all_nodes=len(set(snapshot.truth_labels_all)),
        true_communities_scored_nodes=len(set(snapshot.truth_labels)),
        predicted_communities=len(set(snapshot.predicted_labels)),
    )


def score_snapshot(snapshot: AlignedSnapshot) -> DetectionAMI:
    """Score verified endpoint labels with scikit-learn and synthetic-ami-v1.

    Validate input before applying null policies. Empty/too-small populations,
    constant partitions and all-singleton partitions have explicit reasons;
    missing memberships remain data errors. Negative valid AMI is preserved.
    The optional evaluation dependency is loaded only for eligible frames.
    """
    counts = count_snapshot(snapshot)
    n = counts.assigned_nodes
    status, reason, value = "ok", None, None
    if n == 0:
        status, reason = "empty_scored", "no_scored_users"
    elif n < AMI_POLICY["minimum_scored_users"]:
        status, reason = "insufficient_users", "fewer_than_2_scored_users"
    else:
        flags = []
        for side, groups in (("truth", counts.true_communities_scored_nodes), ("prediction", counts.predicted_communities)):
            if groups == 1:
                flags.append(f"{side}_constant")
            elif groups == n:
                flags.append(f"{side}_all_singletons")
        if flags:
            status, reason = "degenerate_partition", ",".join(flags)
        else:
            try:
                from sklearn.metrics import adjusted_mutual_info_score
            except ModuleNotFoundError as exc:
                if exc.name not in ("sklearn", "sklearn.metrics"):
                    raise
                raise ImportError("AMI requires scikit-learn; install the project extra with pip install -e '.[evaluation]'") from exc
            value = float(adjusted_mutual_info_score(
                snapshot.truth_labels, snapshot.predicted_labels, average_method=AMI_POLICY["average_method"]))
            _require(isfinite(value), "AMI backend returned a nonfinite score")
    return DetectionAMI(month=snapshot.month, n_scored_users=n, ami=value, ami_status=status, ami_reason=reason,
                        ami_policy_id=AMI_POLICY["policy_id"], ami_average_method=AMI_POLICY["average_method"])


def _users_by_month(value):
    _require(isinstance(value, Mapping) and bool(value), "observed users must be a nonempty month mapping")
    result = {}
    for month, users in value.items():
        _require(not isinstance(users, (str, bytes)), "users must be an iterable of identifiers, not a string")
        try:
            result[month] = tuple(users)
        except TypeError as exc:
            raise ValueError("users must be an iterable of identifiers") from exc
    return result


def align_memberships(
    truth: Iterable[Membership], predictions: Iterable[Membership], *,
    truth_reference: str, detector_reference: str,
    active_users_by_month: Mapping[str, Iterable[str]], endpoint_users_by_month: Mapping[str, Iterable[str]],
) -> tuple[AlignedSnapshot, ...]:
    """Require complete truth/endpoint predictions before sorting both vectors.

    Truth covers every active user, including isolates. Predictions must equal
    the independently supplied R endpoint set; never silently intersect sets.
    Preserve all active truth for later coverage/group counts. Empty observed
    months remain explicit snapshots with empty scored vectors, not a score.
    """
    _require(truth_reference != detector_reference, "truth and detector references must differ")
    active, endpoints = _users_by_month(active_users_by_month), _users_by_month(endpoint_users_by_month)
    _require(active.keys() == endpoints.keys(), "active and endpoint observed months must match")
    truth = validate_memberships(truth, expected_reference=truth_reference, expected_users_by_month=active)
    predictions = validate_memberships(predictions, expected_reference=detector_reference, expected_users_by_month=endpoints)
    for month in active:
        _require(set(endpoints[month]) <= set(active[month]), "graph endpoint is outside active users")
    truth_by_user = {(row.month, row.user_id): row.community_id for row in truth}
    predicted_by_user = {(row.month, row.user_id): row.community_id for row in predictions}
    return tuple(AlignedSnapshot(
        month=month, active_user_ids=tuple(sorted(active[month])),
        truth_labels_all=tuple(truth_by_user[month, user] for user in sorted(active[month])),
        user_ids=tuple(sorted(endpoints[month])),
        truth_labels=tuple(truth_by_user[month, user] for user in sorted(endpoints[month])),
        predicted_labels=tuple(predicted_by_user[month, user] for user in sorted(endpoints[month])),
    ) for month in sorted(active))


def _object(value, context):
    _require(isinstance(value, dict), f"{context} must be a JSON object")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _metadata(directory, artifact_type):
    meta = _object(json.loads((directory / "metadata.json").read_text(encoding="utf-8"),
                              object_pairs_hook=_unique_object), "metadata")
    _require(type(meta.get("schema_version")) is int and meta["schema_version"] == 1
             and meta.get("artifact_type") == artifact_type and meta.get("status") == "complete",
             f"a complete {artifact_type} dataset with metadata schema 1 is required")
    return meta


def _checked_file(root, name, files):
    _require(isinstance(name, str) and bool(name) and "\\" not in name
             and not Path(name).is_absolute() and ".." not in Path(name).parts, "invalid relative artifact path")
    path = (root / name).resolve()
    _require(path.is_relative_to(root), "artifact path escapes its dataset")
    info = _object(files.get(name), f"hash entry {name}")
    digest = info.get("sha256")
    _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
             f"invalid SHA-256 entry: {name}")
    _require(sha256(path.read_bytes()).hexdigest() == digest, f"artifact SHA-256 mismatch: {name}")
    return path


def load_aligned_detection(source: Path, detection: Path, *, detector_seed: int = 0) -> AlignedDetection:
    """Read verified PHUC-002/003 datasets without writing to either directory.

    Select exactly one configured detector seed, preserve both references and
    reject mismatched identities, month inventories, graph cohorts or file hashes.
    Absolute paths stored by the producer are advisory; resolve relative files
    from the directories supplied here. No sklearn/igraph installation is needed
    to align persisted inputs; graph provenance uses only standard-library I/O.
    """
    _require(type(detector_seed) is int and detector_seed in (0, 1, 2), "detector_seed must be integer 0, 1 or 2")
    source, detection = source.resolve(), detection.resolve()
    truth_meta = _metadata(source, "synthetic-graph-truth")
    pred_meta = _metadata(detection, "synthetic-detection")
    _require(pred_meta.get("scope") == "detection" and pred_meta.get("completed_stages") == ["detection"]
             and type(pred_meta.get("diagnostics_schema_version")) is int and pred_meta["diagnostics_schema_version"] == 2,
             "a detection-only package with diagnostics schema 2 is required")
    dataset_id = validate_run_id(truth_meta.get("dataset_id"))
    _require(pred_meta.get("dataset_id") == dataset_id
             and truth_meta.get("identity_scope") == pred_meta.get("identity_scope") == dataset_id,
             "dataset/identity scopes must match")
    truth_reference = truth_meta.get("truth_reference")
    _require(truth_reference == f"truth-{dataset_id}" and pred_meta.get("truth_reference") == truth_reference,
             "truth reference must match dataset and detection metadata")
    source_files = _object(truth_meta.get("files"), "source files")
    benchmark = load_benchmark_config(_checked_file(source, "benchmark-config.json", source_files))
    months = benchmark["months"]
    _require(truth_meta.get("observed_months") == pred_meta.get("observed_months") == months,
             "observed months must match source config and detection metadata")
    split = truth_meta.get("split")
    expected = [row for row in dataset_schedule(benchmark, split) if row["dataset_id"] == dataset_id]
    _require(len(expected) == 1, "dataset must belong to its configured split schedule")
    for key, value in expected[0].items():
        _require(type(truth_meta.get(key)) is type(value) and truth_meta[key] == value, f"source dataset context mismatch: {key}")
        # PHUC-003 metadata stores difficulty in its archived runtime config.
        if key != "difficulty" or key in pred_meta:
            _require(type(pred_meta.get(key)) is type(value) and pred_meta[key] == value,
                     f"detection dataset context mismatch: {key}")
    _require(truth_meta.get("graph") == {"directed": False, "simple": True, "weight": 1.0},
             "source must declare a simple undirected unit-weight graph")
    _require(pred_meta.get("graph_protocol") == GRAPH_PROTOCOL == benchmark["protocol"], "graph protocol mismatch")
    _require(type(pred_meta.get("membership_schema_version")) is int and pred_meta["membership_schema_version"] == 1,
             "detector membership schema must be 1")
    recorded_source = _object(_object(pred_meta.get("source"), "detector source").get("files"), "detector source files")
    graph_names = ["metadata.json", "benchmark-config.json"]
    graph_names += [f"snapshots/{month}/{name}.csv" for month in months for name in ("R", "nodes")]
    _require(set(recorded_source) == set(graph_names), "detector must record exactly its source graph/config/metadata files")
    for name in graph_names:
        _checked_file(source, name, recorded_source)
        if name != "metadata.json":
            _checked_file(source, name, source_files)
    inventory = snapshot_inventory(source / "snapshots", protocol=GRAPH_PROTOCOL, expected_months=months)
    _require(pred_meta.get("graph_reference") == inventory["graph_reference"]
             and pred_meta.get("snapshot_cohort_sha256") == inventory["snapshot_cohort_sha256"], "graph cohort reference mismatch")
    detector = _object(pred_meta.get("detector"), "detector config")
    _require(isinstance(detector.get("seeds"), list) and all(type(seed) is int for seed in detector["seeds"])
             and detector["seeds"] == [0, 1, 2] and type(detector.get("canonical_seed")) is int
             and detector["canonical_seed"] == 0 and type(detector.get("gamma")) in (int, float) and detector["gamma"] == 1,
             "week-one detector schedule/gamma/canonical mismatch")
    files = _object(pred_meta.get("files"), "detector files")
    expected_paths = {f"memberships/{month}/membership-seed{seed}.csv" for month in months for seed in (0, 1, 2)}
    _require(set(files) == expected_paths | {"detection.json", "detector-config.json"}, "detector file inventory mismatch")
    for name in files:
        _checked_file(detection, name, files)
    _require(detector.get("config_file") == "detector-config.json"
             and detector.get("config_sha256") == files["detector-config.json"]["sha256"], "detector config mapping mismatch")
    runtime = load_benchmark_config(detection / "detector-config.json")
    _require({k: v for k, v in runtime.items() if k != "detector"} == {k: v for k, v in benchmark.items() if k != "detector"}
             and runtime["detector"] == {"seeds": detector["seeds"], "gamma": detector["gamma"], "canonical_seed": 0},
             "runtime/source graph recipe or detector config mismatch")
    references = _object(pred_meta.get("detector_references"), "detector references")
    _require(set(references) == {"0", "1", "2"} and all(isinstance(ref, str) for ref in references.values())
             and len(set(references.values())) == 3,
             "each detector seed must have one distinct reference")
    for seed in (0, 1, 2):
        reference = references[str(seed)]
        _require(isinstance(reference, str) and reference.startswith(f"{dataset_id}:{inventory['graph_reference']}:")
                 and reference.endswith(f"-gamma1-seed{seed}") and reference != truth_reference,
                 "detector reference does not match dataset/cohort/seed")
    entries = pred_meta.get("memberships")
    _require(isinstance(entries, list) and len(entries) == len(months) * 3, "membership mapping must cover every month/seed")
    mappings = {}
    month_hashes = {row["month"]: row["graph_sha256"] for row in inventory["month_graphs"]}
    for entry in entries:
        entry = _object(entry, "membership mapping")
        month, seed = entry.get("month"), entry.get("seed")
        _require(isinstance(month, str) and month in months and type(seed) is int and seed in (0, 1, 2),
                 "membership mapping has invalid month/seed")
        name = f"memberships/{month}/membership-seed{seed}.csv"
        _require((month, seed) not in mappings and entry.get("dataset_id") == entry.get("identity_scope") == dataset_id
                 and entry.get("reference_id") == references[str(seed)] and entry.get("path") == name
                 and entry.get("sha256") == files[name]["sha256"]
                 and type(entry.get("canonical")) is bool and entry["canonical"] == (seed == 0)
                 and entry.get("graph_sha256") == month_hashes[month]
                 and entry.get("graph_file") == f"snapshots/{month}/R.csv"
                 and entry.get("nodes_file") == f"snapshots/{month}/nodes.csv", "membership dataset/reference/path mapping mismatch")
        mappings[month, seed] = entry
    active, endpoints = {}, {}
    for month in months:
        active[month] = read_nodes(source / f"snapshots/{month}/nodes.csv", expected_month=month)
        edges = read_edges(source / f"snapshots/{month}/R.csv", expected_month=month, expected_users=active[month])
        _require(all(edge.weight == 1 for edge in edges), "source edges must have weight 1")
        endpoints[month] = {user for edge in edges for user in (edge.source_user_id, edge.target_user_id)}
    truth = read_memberships(_checked_file(source, "truth/membership.csv", source_files), expected_reference=truth_reference,
                             expected_users_by_month=active)
    predicted = tuple(row for month in months for row in read_memberships(
        detection / mappings[month, detector_seed]["path"], expected_reference=references[str(detector_seed)],
        expected_users_by_month={month: endpoints[month]}))
    aligned = align_memberships(truth, predicted, truth_reference=truth_reference, detector_reference=references[str(detector_seed)],
                                active_users_by_month=active, endpoint_users_by_month=endpoints)
    return AlignedDetection(**expected[0], identity_scope=dataset_id, detector_seed=detector_seed, gamma=float(detector["gamma"]),
                            truth_reference=truth_reference, detector_reference=references[str(detector_seed)], snapshots=aligned)


def _summary_rows(metrics):
    groups = {}
    for row in metrics:
        for level in ("scenario", "all_scenarios"):
            key = (level, row["split"], row["scenario"] if level == "scenario" else "",
                   row["difficulty"], row["gamma"], row["detector_seed"])
            groups.setdefault(key, []).append(row)
    summaries = []
    for (level, split, scenario, difficulty, gamma, seed), rows in sorted(groups.items()):
        valid = [row["ami"] for row in rows if row["ami_status"] == "ok"]
        coverage = [row["coverage"] for row in rows if row["coverage"] is not None]
        statuses = Counter(row["ami_status"] for row in rows)
        reasons = Counter(row["ami_reason"] for row in rows if row["ami_status"] != "ok")
        summaries.append({
            "aggregation_level": level, "split": split, "scenario": scenario, "difficulty": difficulty,
            "gamma": gamma, "detector_seed": seed, "seed_role": "canonical" if seed == 0 else "diagnostic",
            "aggregation_unit": "dataset-month", "ami_aggregation": SUMMARY_POLICY["ami_aggregation"],
            "coverage_aggregation": SUMMARY_POLICY["coverage_aggregation"],
            "n_datasets": len({row["dataset_id"] for row in rows}), "n_rows": len(rows),
            "n_ami_valid": len(valid), "n_ami_missing": len(rows) - len(valid),
            "n_empty_scored": statuses["empty_scored"], "n_insufficient_users": statuses["insufficient_users"],
            "n_degenerate_partition": statuses["degenerate_partition"],
            "ami_missing_reasons": json.dumps(dict(sorted(reasons.items())), sort_keys=True, separators=(",", ":")),
            "ami_mean": fmean(valid) if valid else None, "ami_min": min(valid) if valid else None,
            "ami_max": max(valid) if valid else None,
            "n_coverage_valid": len(coverage), "n_coverage_missing": len(rows) - len(coverage),
            "coverage_mean": fmean(coverage) if coverage else None,
            "n_scored_user_observations": sum(row["n_scored_users"] for row in rows),
            "n_active_user_observations": sum(row["active_nodes"] for row in rows),
        })
    return summaries


def _report_input_files(directory, artifact_type):
    meta = _metadata(directory, artifact_type)
    declared = _object(meta.get("files"), "input files")
    files = {name: sha256(_checked_file(directory, name, declared).read_bytes()).hexdigest() for name in declared}
    files["metadata.json"] = sha256((directory / "metadata.json").read_bytes()).hexdigest()
    # These optional sidecars also contribute to snapshot_inventory fingerprints.
    months = meta.get("observed_months")
    _require(isinstance(months, list) and bool(months) and all(isinstance(month, str) for month in months),
             "input observed_months must be a nonempty month list")
    for month in months:
        next_month(month)
        for name in ("directed_R.csv", "users.csv", "node_order.csv"):
            relative = f"snapshots/{month}/{name}"
            path = (directory / relative).resolve()
            _require(path.is_relative_to(directory), "input sidecar escapes its dataset")
            if path.is_file():
                files[relative] = sha256(path.read_bytes()).hexdigest()
    return meta, dict(sorted(files.items()))


def _stored_detection_timings(directory, meta, aligned):
    diagnostics = _object(json.loads((directory / "detection.json").read_text(encoding="utf-8"),
                                     object_pairs_hook=_unique_object), "detection diagnostics")
    months = [frame.month for frame in aligned.snapshots]
    _require(type(diagnostics.get("schema_version")) is int and diagnostics["schema_version"] == 2
             and diagnostics.get("dataset_id") == diagnostics.get("identity_scope") == aligned.dataset_id
             and diagnostics.get("graph_reference") == meta["graph_reference"]
             and diagnostics.get("actual_months") == months
             and isinstance(diagnostics.get("detector_seeds"), list)
             and all(type(seed) is int for seed in diagnostics["detector_seeds"])
             and diagnostics["detector_seeds"] == [0, 1, 2]
             and type(diagnostics.get("canonical_seed")) is int and diagnostics["canonical_seed"] == 0,
             "stored timing diagnostics identity/schedule mismatch")
    entries = diagnostics.get("months")
    _require(isinstance(entries, list) and all(isinstance(row, dict) for row in entries)
             and [row.get("month") for row in entries] == months, "stored timing months must match observed snapshots")
    result = []
    frames = {frame.month: frame for frame in aligned.snapshots}
    graph_hashes = {row["month"]: row["graph_sha256"] for row in meta["memberships"] if row["seed"] == 0}
    for row in entries:
        seconds, runs = row.get("wall_seconds"), row.get("runs")
        _require(type(seconds) in (int, float) and isfinite(seconds) and seconds >= 0,
                 "stored detection wall_seconds must be finite and nonnegative")
        expected_status = "complete" if frames[row["month"]].user_ids else "empty_graph_no_partition"
        _require(isinstance(runs, list) and len(runs) == 3 and all(isinstance(run, dict) for run in runs)
                 and all(type(run.get("seed")) is int for run in runs)
                 and [run["seed"] for run in runs] == [0, 1, 2]
                 and row.get("graph_sha256") == graph_hashes[row["month"]]
                 and all(run.get("reference_id") == meta["detector_references"][str(run["seed"])]
                         and run.get("status") == expected_status for run in runs),
                 "stored timing must cover the three configured seed references")
        result.append({"dataset_id": aligned.dataset_id, "month": row["month"], "detector_seeds": [0, 1, 2],
                       "wall_seconds": seconds, "scope": "all configured seeds for one observed month",
                       "source_file": "detection.json", "source_sha256": meta["files"]["detection.json"]["sha256"]})
    return result


def _write_report_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_report_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def export_detection_evaluation(pairs: Iterable[tuple[Path, Path]], output: Path) -> dict:
    """Export one new report for unique PHUC-002/003 dataset pairs.

    Load and score all configured seeds, retain null rows and summarize each
    seed independently. Stored detection timing is copied once per dataset-month;
    it is not a fresh measurement or a separate measurement for each seed.
    Validate and recheck inputs before reserving output. A publication I/O error
    leaves partial files with failure.json; complete metadata is written last.
    """
    started = datetime.now(timezone.utc).isoformat()
    start = perf_counter()
    _require(not isinstance(pairs, (str, bytes, Path)), "pairs must be an iterable of source/detection path pairs")
    pairs = tuple(pairs)
    _require(bool(pairs), "at least one source/detection dataset pair is required")
    output = Path(output).resolve()
    _require(output.parent.is_dir() and not output.exists(), "output parent must exist and report directory must be new")
    normalized = []
    for pair in pairs:
        _require(isinstance(pair, (tuple, list)) and len(pair) == 2
                 and all(isinstance(path, (str, Path)) for path in pair), "each pair must contain source and detection paths")
        source, detected = (Path(path).resolve() for path in pair)
        for directory in (source, detected):
            _require(directory.is_dir(), "input dataset directory does not exist")
            _require(not output.is_relative_to(directory) and not directory.is_relative_to(output),
                     "report output must not overlap either input dataset")
        normalized.append((source, detected))
    versions = {"python": platform.python_version()}
    for package in ("reddit-community-evolution", "scikit-learn", "numpy", "scipy"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    metrics, timings, inputs, identities = [], [], [], set()
    compute_seconds = 0.0
    for source, detected in normalized:
        source_meta, source_files = _report_input_files(source, "synthetic-graph-truth")
        detected_meta, detected_files = _report_input_files(detected, "synthetic-detection")
        dataset_id = validate_run_id(source_meta.get("dataset_id"))
        _require(dataset_id not in identities, "duplicate dataset_id in report; keep different cohorts in separate reports")
        identities.add(dataset_id)
        for seed in (0, 1, 2):
            aligned = load_aligned_detection(source, detected, detector_seed=seed)
            for frame in aligned.snapshots:
                compute_start = perf_counter()
                counts, score = count_snapshot(frame), score_snapshot(frame)
                compute_seconds += perf_counter() - compute_start
                metrics.append({
                    "dataset_id": aligned.dataset_id, "identity_scope": aligned.identity_scope, "split": aligned.split,
                    "scenario": aligned.scenario, "difficulty": aligned.difficulty, "generator_seed": aligned.generator_seed,
                    "month": frame.month, "detector_seed": seed, "gamma": aligned.gamma, "canonical": seed == 0,
                    "truth_reference": aligned.truth_reference, "detector_reference": aligned.detector_reference,
                    **asdict(counts), **asdict(score), "sklearn_version": versions["scikit-learn"],
                })
            if seed == 0:
                timings.extend(_stored_detection_timings(detected, detected_meta, aligned))
        inputs.append({"dataset_id": dataset_id, "source_directory": str(source), "detection_directory": str(detected),
                       "source_files": source_files, "detection_files": detected_files,
                       "detector_versions": detected_meta["detector"]["versions"]})
    metrics.sort(key=lambda row: (row["dataset_id"], row["month"], row["detector_seed"]))
    summaries = _summary_rows(metrics)
    for (source, detected), entry in zip(normalized, inputs, strict=True):
        _require(_report_input_files(source, "synthetic-graph-truth")[1] == entry["source_files"]
                 and _report_input_files(detected, "synthetic-detection")[1] == entry["detection_files"],
                 "evaluation inputs changed while preparing the report")
    evaluation_seconds = perf_counter() - start
    output.mkdir(exist_ok=False)
    try:
        export_start = perf_counter()
        _write_report_json(output / "ami-policy.json", dict(AMI_POLICY))
        _write_report_csv(output / "detection_metrics.csv", metrics)
        _write_report_csv(output / "detection_summary.csv", summaries)
        timing = {
            "generation_wall_seconds": None, "generation_scope": "not measured by evaluator",
            "detection_wall_seconds": sum(row["wall_seconds"] for row in timings),
            "detection_scope": "sum of stored per-month timings over all three seeds; not rerun or measured per seed",
            "detection_by_month": sorted(timings, key=lambda row: (row["dataset_id"], row["month"])),
            "evaluation_wall_seconds": evaluation_seconds,
            "evaluation_scope": "preflight/input verification and loading, counts/AMI for all seeds and summary; excludes output writes",
            "evaluation_compute_wall_seconds": compute_seconds,
            "evaluation_compute_scope": "counts and AMI calls only, over all rows",
            "csv_export_wall_seconds": perf_counter() - export_start,
            "csv_export_scope": "policy and both CSV writes; excludes timing and metadata writes",
            "peak_memory_bytes": None, "peak_memory_scope": "not measured",
        }
        _write_report_json(output / "timing.json", timing)
        files = {name: {"sha256": sha256((output / name).read_bytes()).hexdigest()} for name in (
            "ami-policy.json", "detection_metrics.csv", "detection_summary.csv", "timing.json")}
        meta = {"schema_version": 1, "artifact_type": "synthetic-detection-evaluation", "status": "complete",
                "scope": "detection-evaluation-only", "completed_stages": ["evaluation"],
                "created_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
                "dataset_count": len(inputs), "metric_rows": len(metrics), "summary_rows": len(summaries),
                "ami_valid_rows": sum(row["ami_status"] == "ok" for row in metrics),
                "ami_missing_rows": sum(row["ami_status"] != "ok" for row in metrics),
                "metric_key": ["dataset_id", "month", "detector_seed"], "detector_seeds": [0, 1, 2],
                "canonical_seed": 0, "summary_policy": dict(SUMMARY_POLICY), "ami_policy": dict(AMI_POLICY),
                "versions": versions, "evaluator_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                "inputs": sorted(inputs, key=lambda row: row["dataset_id"]), "files": files}
        _write_report_json(output / "metadata.pending.json", meta)
        (output / "metadata.pending.json").rename(output / "metadata.json")
        return meta
    except Exception as exc:
        try:
            _write_report_json(output / "failure.json", {"status": "failed", "scope": "detection-evaluation-only",
                                                       "error_type": type(exc).__name__, "message": str(exc)})
        except OSError:
            pass
        raise


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Export synthetic detection metrics and per-seed summaries to a new directory.")
    parser.add_argument("--pair", nargs=2, action="append", required=True, type=Path, metavar=("SOURCE", "DETECTION"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        meta = export_detection_evaluation(args.pair, args.output)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"evaluation error: {exc}\n")
    print(json.dumps({"status": meta["status"], "datasets": meta["dataset_count"], "metric_rows": meta["metric_rows"],
                      "summary_rows": meta["summary_rows"], "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
