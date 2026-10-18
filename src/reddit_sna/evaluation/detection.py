"""Verify synthetic truth/detector inputs and align labels by user ID.

This module does not yet calculate AMI, coverage, summaries or timing metrics.
Community names are preserved; aligning users is not community matching.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from reddit_sna.benchmarks.config import GRAPH_PROTOCOL, dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.io import read_edges, read_memberships, read_nodes, validate_memberships
from reddit_sna.config import validate_run_id
from reddit_sna.contracts import Membership
from reddit_sna.graphs.provenance import snapshot_inventory


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


def _require(condition, message):
    if not condition:
        raise ValueError(message)


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
