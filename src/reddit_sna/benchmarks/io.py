"""Strict CSV adapters for synthetic node lists and non-overlapping memberships.

Callers supply the observed months, expected users and reference explicitly.
Truth should be checked against all active users; detector memberships against
the expected graph endpoints. Empty observed months are allowed explicitly.
Writers validate before opening a new file and never overwrite existing files.
"""

from collections.abc import Iterable, Mapping
import csv
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform

from reddit_sna.benchmarks.scenarios import build_memberships, build_transitions
from reddit_sna.config import validate_run_id
from reddit_sna.contracts import Membership, SCHEMA_VERSION, SnapshotEdge, next_month

NODE_COLUMNS = ("month", "user_id")
EDGE_COLUMNS = ("month", "source_user_id", "target_user_id", "weight")
MEMBERSHIP_COLUMNS = ("reference_id", "month", "community_id", "user_id")
EVENT_COLUMNS = ("reference_id", "source_month", "source_community_id", "target_month", "event")
LINK_COLUMNS = ("reference_id", "source_month", "source_community_id", "target_month", "target_community_id")


def _checked_users(month: str, user_ids: Iterable[str]) -> tuple[str, ...]:
    next_month(month)
    if isinstance(user_ids, (str, bytes)):
        raise ValueError("users must be an iterable of identifiers, not one string")
    try:
        users = tuple(user_ids)
    except TypeError as exc:
        raise ValueError("users must be an iterable of identifiers") from exc
    if any(not isinstance(uid, str) or not uid.strip() for uid in users):
        raise ValueError("user identifiers must be nonempty strings")
    if len(set(users)) != len(users):
        raise ValueError("duplicate user in node list")
    return tuple(sorted(users))


def _read_rows(path: Path, columns: tuple[str, ...]) -> list[list[str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            if next(reader, None) != list(columns):
                raise ValueError("CSV header does not match the expected schema")
            rows = list(reader)
    except csv.Error as exc:
        raise ValueError("malformed CSV") from exc
    if any(len(row) != len(columns) for row in rows):
        raise ValueError("CSV row width does not match the expected schema")
    return rows


def _write_rows(path: Path, columns: tuple[str, ...], rows: Iterable[tuple]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def write_nodes(path: Path, month: str, user_ids: Iterable[str]) -> None:
    """Write one observed month's users in canonical order to a new CSV.

    An empty list writes a header-only observed month. The parent directory
    must already exist; this function does not choose or create a run folder.
    """
    users = _checked_users(month, user_ids)
    _write_rows(path, NODE_COLUMNS, ((month, uid) for uid in users))


def read_nodes(path: Path, *, expected_month: str) -> tuple[str, ...]:
    """Read one observed month's complete node list, including isolates."""
    next_month(expected_month)
    rows = _read_rows(path, NODE_COLUMNS)
    if any(month != expected_month for month, _ in rows):
        raise ValueError("node month does not match the expected month")
    return _checked_users(expected_month, (uid for _, uid in rows))


def validate_edges(
    edges: Iterable[SnapshotEdge], *, expected_month: str, expected_users: Iterable[str],
) -> tuple[SnapshotEdge, ...]:
    """Require a simple undirected snapshot with canonical endpoints.

    Active users are supplied independently, including isolates. Reversed pairs
    are rejected rather than silently normalized or combined with duplicates.
    """
    users = set(_checked_users(expected_month, expected_users))
    rows, seen = tuple(edges), set()
    for row in rows:
        if not isinstance(row, SnapshotEdge):
            raise ValueError("edges must contain SnapshotEdge records")
        if row.month != expected_month:
            raise ValueError("edge month does not match the expected month")
        if row.source_user_id >= row.target_user_id:
            raise ValueError("undirected endpoints must satisfy source < target")
        if row.source_user_id not in users or row.target_user_id not in users:
            raise ValueError("edge endpoint is outside the expected users")
        if type(row.weight) not in (int, float):
            raise ValueError("edge weight must be a number, not bool")
        pair = (row.source_user_id, row.target_user_id)
        if pair in seen:
            raise ValueError("duplicate undirected edge")
        seen.add(pair)
    return tuple(sorted(rows, key=lambda row: (row.source_user_id, row.target_user_id)))


def write_edges(
    path: Path, edges: Iterable[SnapshotEdge], *, expected_month: str, expected_users: Iterable[str],
) -> None:
    """Validate before opening a new R.csv; write UTF-8/LF in sorted order."""
    rows = validate_edges(edges, expected_month=expected_month, expected_users=expected_users)
    _write_rows(path, EDGE_COLUMNS, (
        (row.month, row.source_user_id, row.target_user_id, float(row.weight)) for row in rows
    ))


def read_edges(
    path: Path, *, expected_month: str, expected_users: Iterable[str],
) -> tuple[SnapshotEdge, ...]:
    """Read R.csv without inferring the active user list from its endpoints."""
    rows = (SnapshotEdge(month, source, target, float(weight))
            for month, source, target, weight in _read_rows(path, EDGE_COLUMNS))
    return validate_edges(rows, expected_month=expected_month, expected_users=expected_users)


def validate_memberships(
    memberships: Iterable[Membership],
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> tuple[Membership, ...]:
    """Require exactly one membership per expected user in one reference.

    Declared months must be consecutive, with at least one observed month.
    Empty months must be included explicitly with an empty user iterable.
    Return records sorted by month, community and user without changing IDs.
    """
    if not isinstance(expected_reference, str) or not expected_reference.strip():
        raise ValueError("expected reference must be a nonempty string")
    if not isinstance(expected_users_by_month, Mapping) or not expected_users_by_month:
        raise ValueError("at least one observed month and its users must be declared")
    expected = {
        month: set(_checked_users(month, users))
        for month, users in expected_users_by_month.items()
    }
    months = sorted(expected)
    if any(next_month(a) != b for a, b in zip(months, months[1:])):
        raise ValueError("declared membership months must be consecutive")

    rows = tuple(memberships)
    seen = {month: set() for month in months}
    for row in rows:
        if not isinstance(row, Membership):
            raise ValueError("memberships must contain Membership records")
        if row.reference_id != expected_reference:
            raise ValueError("membership reference does not match the expected reference")
        if row.month not in expected:
            raise ValueError("membership month is outside the declared months")
        if row.user_id in seen[row.month]:
            raise ValueError("duplicate membership for a user in one month")
        if row.user_id not in expected[row.month]:
            raise ValueError("membership contains an unexpected user")
        seen[row.month].add(row.user_id)
    if any(seen[month] != users for month, users in expected.items()):
        raise ValueError("memberships are missing expected users")
    return tuple(sorted(rows, key=lambda row: (row.month, row.community_id, row.user_id)))


def write_memberships(
    path: Path,
    memberships: Iterable[Membership],
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> None:
    """Validate and write canonical memberships to a new UTF-8 CSV."""
    rows = validate_memberships(
        memberships,
        expected_reference=expected_reference,
        expected_users_by_month=expected_users_by_month,
    )
    _write_rows(
        path,
        MEMBERSHIP_COLUMNS,
        ((row.reference_id, row.month, row.community_id, row.user_id) for row in rows),
    )


def read_memberships(
    path: Path,
    *,
    expected_reference: str,
    expected_users_by_month: Mapping[str, Iterable[str]],
) -> tuple[Membership, ...]:
    """Read and validate a complete membership table against caller expectations."""
    rows = (Membership(*fields) for fields in _read_rows(path, MEMBERSHIP_COLUMNS))
    return validate_memberships(
        rows,
        expected_reference=expected_reference,
        expected_users_by_month=expected_users_by_month,
    )


def export_truth_fixture(
    destination: Path,
    *,
    scenario: str,
    dataset_id: str,
    generator_seed: int,
    start_month: str = "2020-01",
) -> dict:
    """Create one complete stable/grow truth dataset in a new directory.

    The parent must exist. Data is read back before metadata is written last.
    A failed export keeps its partial files, with no complete metadata marker.
    The seed is provenance reserved for later graph sampling; truth is fixed.
    """
    if scenario not in ("stable", "grow"):
        raise ValueError("truth fixture export currently supports only stable/grow")
    validate_run_id(dataset_id)
    if type(generator_seed) is not int or not 0 <= generator_seed < 2**32:
        raise ValueError("generator_seed must be an integer in [0, 2**32)")
    reference = f"truth-{dataset_id}"
    memberships = build_memberships(scenario, reference, start_month=start_month)
    transitions = build_transitions(scenario, reference, start_month=start_month)
    months = (start_month, next_month(start_month))
    users = {month: tuple(row.user_id for row in memberships if row.month == month) for month in months}
    package_version = version("reddit-community-evolution")
    events = [
        [row.source.reference_id, row.source.feature_month, row.source.community_id,
         row.target_month, row.event.value]
        for row in transitions.events
    ]
    links = [
        [row.source.reference_id, row.source.feature_month, row.source.community_id,
         row.target.feature_month, row.target.community_id]
        for row in transitions.links
    ]
    destination.mkdir(exist_ok=False)
    (destination / "truth").mkdir()
    for month in months:
        snapshot = destination / "snapshots" / month
        snapshot.mkdir(parents=True)
        write_nodes(snapshot / "nodes.csv", month, users[month])
    expected = dict(expected_reference=reference, expected_users_by_month=users)
    write_memberships(destination / "truth/membership.csv", memberships, **expected)
    _write_rows(destination / "truth/events.csv", EVENT_COLUMNS, events)
    _write_rows(destination / "truth/links.csv", LINK_COLUMNS, links)

    for month in months:
        if read_nodes(destination / f"snapshots/{month}/nodes.csv", expected_month=month) != users[month]:
            raise ValueError("exported nodes differ from scenario truth")
    if read_memberships(destination / "truth/membership.csv", **expected) != memberships:
        raise ValueError("exported memberships differ from scenario truth")
    if _read_rows(destination / "truth/events.csv", EVENT_COLUMNS) != events:
        raise ValueError("exported events differ from scenario truth")
    if _read_rows(destination / "truth/links.csv", LINK_COLUMNS) != links:
        raise ValueError("exported links differ from scenario truth")

    files = [f"snapshots/{month}/nodes.csv" for month in months]
    files += ["truth/membership.csv", "truth/events.csv", "truth/links.csv"]
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "synthetic-truth-fixture",
        "status": "complete",
        "dataset_id": dataset_id,
        "split": "development",
        "scenario": scenario,
        "difficulty": "easy",
        "identity_scope": dataset_id,
        "observed_months": list(months),
        "truth_reference": reference,
        "detector_references": {},
        "generator": {
            "name": "planted-stable-grow", "version": 1,
            "seed": generator_seed, "seed_used_for_truth": False,
            "config": {"scenario": scenario, "start_month": start_month,
                       "source_size": 12, "target_size": 12 if scenario == "stable" else 18,
                       "background_size": 12},
        },
        "environment": {"python_version": platform.python_version(), "package_version": package_version},
        "counts": {"nodes_by_month": {month: len(users[month]) for month in months},
                   "memberships": len(memberships), "events": len(events), "links": len(links)},
        "files": {name: {"sha256": sha256((destination / name).read_bytes()).hexdigest()}
                  for name in files},
    }
    with (destination / "metadata.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    return metadata


def export_graph_dataset(
    destination: Path, *, benchmark: dict, scenario: str, generator_seed: int,
    split: str = "development",
) -> dict:
    """Export one scheduled graph/truth dataset, writing complete metadata last.

    The parent must exist and the destination must be new, even if empty.
    Config/selection/sampled records are validated before reserving output.
    Failed exports retain partial files without complete metadata. This does
    not run a detector, tracker or evaluation, or freeze the benchmark config.
    """
    # Local imports avoid the sampler -> CSV validator -> config import cycle.
    from reddit_sna.benchmarks.config import dataset_schedule
    from reddit_sna.benchmarks.dynamic import sample_snapshots

    if type(generator_seed) is not int or not 0 <= generator_seed < 2**32:
        raise ValueError("generator_seed must be an integer in [0, 2**32)")
    choices = [item for item in dataset_schedule(benchmark, split)
               if item["scenario"] == scenario and item["generator_seed"] == generator_seed]
    if len(choices) != 1:
        raise ValueError("scenario and generator_seed must belong to the selected split schedule")
    selected = choices[0]
    dataset_id = selected["dataset_id"]
    reference = f"truth-{dataset_id}"
    months = benchmark["months"]
    generator = benchmark["generator"]
    memberships = build_memberships(scenario, reference, start_month=months[0])
    transitions = build_transitions(scenario, reference, start_month=months[0])
    # This registry is from trusted planted truth, never an unvalidated input CSV.
    users = {month: tuple(row.user_id for row in memberships if row.month == month) for month in months}
    expected = dict(expected_reference=reference, expected_users_by_month=users)
    snapshots = sample_snapshots(
        memberships, **expected, generator_seed=generator_seed,
        p_in=generator["p_in"], p_out=generator["p_out"],
    )
    for snapshot in snapshots:
        validate_edges(snapshot.edges, expected_month=snapshot.month, expected_users=snapshot.nodes)
    events = [[row.source.reference_id, row.source.feature_month, row.source.community_id,
               row.target_month, row.event.value] for row in transitions.events]
    links = [[row.source.reference_id, row.source.feature_month, row.source.community_id,
              row.target.feature_month, row.target.community_id] for row in transitions.links]
    package_version = version("reddit-community-evolution")
    config_text = json.dumps(benchmark, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    destination.mkdir(exist_ok=False)
    (destination / "truth").mkdir()
    for snapshot in snapshots:
        folder = destination / "snapshots" / snapshot.month
        folder.mkdir(parents=True)
        write_nodes(folder / "nodes.csv", snapshot.month, snapshot.nodes)
        write_edges(folder / "R.csv", snapshot.edges,
                    expected_month=snapshot.month, expected_users=snapshot.nodes)
    write_memberships(destination / "truth/membership.csv", memberships, **expected)
    _write_rows(destination / "truth/events.csv", EVENT_COLUMNS, events)
    _write_rows(destination / "truth/links.csv", LINK_COLUMNS, links)
    with (destination / "benchmark-config.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(config_text)

    for snapshot in snapshots:
        folder = destination / "snapshots" / snapshot.month
        if read_nodes(folder / "nodes.csv", expected_month=snapshot.month) != snapshot.nodes:
            raise ValueError("exported nodes differ from sampled snapshot")
        if read_edges(folder / "R.csv", expected_month=snapshot.month,
                      expected_users=snapshot.nodes) != snapshot.edges:
            raise ValueError("exported edges differ from sampled snapshot")
    if read_memberships(destination / "truth/membership.csv", **expected) != memberships:
        raise ValueError("exported memberships differ from scenario truth")
    if _read_rows(destination / "truth/events.csv", EVENT_COLUMNS) != events:
        raise ValueError("exported events differ from scenario truth")
    if _read_rows(destination / "truth/links.csv", LINK_COLUMNS) != links:
        raise ValueError("exported links differ from scenario truth")
    if (destination / "benchmark-config.json").read_text(encoding="utf-8") != config_text:
        raise ValueError("exported config differs from requested benchmark")

    files = sorted(path.relative_to(destination).as_posix()
                   for path in destination.rglob("*") if path.is_file())
    metadata = {
        "schema_version": SCHEMA_VERSION, "artifact_type": "synthetic-graph-truth",
        "status": "complete", **selected, "identity_scope": dataset_id,
        "observed_months": list(months), "truth_reference": reference, "detector_references": {},
        "graph": {"directed": False, "simple": True, "weight": 1.0},
        "ordering": benchmark["ordering"],
        "generator": {
            "name": "planted-six-events", "version": 1, "seed": generator_seed,
            "seed_used_for_truth": False, "sampler_version": generator["sampler_version"],
            "rng_protocol": generator["rng_protocol"],
            "config": {"scenario": scenario, "months": list(months),
                       "p_in": generator["p_in"], "p_out": generator["p_out"], "weight": 1.0},
        },
        "environment": {"python_version": platform.python_version(), "package_version": package_version},
        "counts": {
            "nodes_by_month": {s.month: len(s.nodes) for s in snapshots},
            "edges_by_month": {s.month: len(s.edges) for s in snapshots},
            "communities_by_month": {
                month: len({row.community_id for row in memberships if row.month == month}) for month in months
            },
            "isolates_by_month": {
                s.month: len(set(s.nodes) - {uid for edge in s.edges
                                            for uid in (edge.source_user_id, edge.target_user_id)})
                for s in snapshots
            },
            "memberships": len(memberships), "events": len(events), "links": len(links),
        },
        "files": {name: {"sha256": sha256((destination / name).read_bytes()).hexdigest()} for name in files},
    }
    with (destination / "metadata.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    return metadata
