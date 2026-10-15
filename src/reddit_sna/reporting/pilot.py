"""Read an immutable preparation run chain before exposing data for plotting.

Replay is an audit of recorded results, not a new raw-data experiment. All paths
are confined to project artifacts; source hashes describe the original producer.
"""

import csv
import json
from pathlib import Path

from reddit_sna.data.archive import digest_file
from reddit_sna.graphs.audit import OUTCOMES
from reddit_sna.graphs.provenance import snapshot_inventory


def read_json(path: Path) -> dict:
    """Read UTF-8 research metadata without loading discussion text or identities."""
    return json.loads(path.read_text(encoding="utf-8"))


def verified_manifest(run: Path, artifact_root: Path) -> dict:
    """Require completion and verify every declared artifact, including SQLite.

    Hashes detect changes relative to the recorded manifest, not malicious
    replacement of both manifest and contents; manifests are trusted local input.
    """
    run, artifact_root = run.resolve(), artifact_root.resolve()
    if not run.is_relative_to(artifact_root):
        raise ValueError("Replay run must stay inside project artifacts")
    if not (run / "manifest.json").is_file():
        raise ValueError("Replay manifest missing. Run prepare first, then set REDDIT_DETECTION_RUN to its run ID")
    manifest = read_json(run / "manifest.json")
    if manifest.get("status") not in {"complete", "complete_through_detection"}:
        raise ValueError("Replay requires a completed run")
    if not manifest.get("artifact_hashes"):
        raise ValueError("Replay requires recorded artifact hashes")
    for relative, expected in manifest["artifact_hashes"].items():
        path = (run / relative).resolve()
        if not path.is_relative_to(run) or digest_file(path) != expected:
            raise ValueError("Replay artifact hash mismatch or unsafe artifact path")
    return manifest


def resolve_runs(project: Path, detection_run: str | None = None) -> dict[str, Path]:
    """Resolve one detection run and its recorded graph/normalization ancestors.

    Automatic selection is allowed only for one candidate. Multiple experiments
    must be selected explicitly, never ranked by their quality or modification time.
    """
    root = (project / "artifacts").resolve()
    if detection_run is None:
        candidates = sorted(p.parent for p in (root / "core").glob("*/detection.json"))
        if len(candidates) != 1:
            raise ValueError("Set REDDIT_DETECTION_RUN explicitly: missing or ambiguous detection runs")
        detection = candidates[0]
    else:
        detection = root / "core" / detection_run
    runs = {"detection": detection.resolve()}
    for child, parent in (("detection", "graphs"), ("graphs", "normalized")):
        manifest = verified_manifest(runs[child], root)
        # An all-stage run owns all three products; separate stages record ancestors.
        source = manifest.get("source_run")
        runs[parent] = Path(source).resolve() if source else runs[child]
        verified_manifest(runs[parent], root)
        if source and digest_file(runs[parent] / "manifest.json") != manifest.get("source_manifest_sha256"):
            raise ValueError("Replay source manifest hash mismatch")
    return runs


def load_pilot(project: Path, detection_run: str | None = None) -> dict:
    """Return verified plot inputs; reject period, identity and count mismatches.

    Returns a mapping containing runs, manifests, normalization, graphs, detection
    and corpus audit. No raw Reddit text, author lookup or private keys are read.
    """
    runs = resolve_runs(project, detection_run)
    manifests = {k: read_json(p / "manifest.json") for k, p in runs.items()}
    required = {"normalized": ("normalization.json", "corpus_manifest.json"),
                "graphs": ("snapshots.json",), "detection": ("detection.json",)}
    for stage, names in required.items():
        if not all(name in manifests[stage]["artifact_hashes"] for name in names):
            raise ValueError("Replay metadata must have declared artifact hashes")
    normalization = read_json(runs["normalized"] / "normalization.json")
    graphs = read_json(runs["graphs"] / "snapshots.json")
    detection = read_json(runs["detection"] / "detection.json")
    actual = snapshot_inventory(runs["graphs"] / "snapshots", protocol=graphs["graph_protocol"],
                                expected_months=graphs["actual_months"])
    for field in ("graph_reference", "actual_months", "start_month", "end_month_exclusive", "month_graphs"):
        if not (actual[field] == graphs[field] == detection[field]):
            raise ValueError(f"Replay graph/detection mismatch: {field}")
    if not (normalization["identity_scope"] == graphs["identity_scope"]
            == manifests["detection"]["identity_scope"]):
        raise ValueError("Replay identity scope mismatch")
    for field in ("actual_months", "start_month", "end_month_exclusive", "graph_reference"):
        if manifests["detection"].get(field) != detection[field]:
            raise ValueError(f"Replay detection manifest mismatch: {field}")
    cells = graphs["corpus_month_audit"]
    expected = {(c, m) for c in graphs["declared_corpora"] for m in actual["actual_months"]}
    if len(cells) != len(expected) or {(r["corpus"], r["month"]) for r in cells} != expected:
        raise ValueError("Replay corpus-month grid is incomplete or duplicated")
    for row in cells:
        if (set(row["reply_outcomes"]) != set(OUTCOMES)
                or any(v < 0 for v in row["reply_outcomes"].values())
                or sum(row["reply_outcomes"].values()) != row["comments"]
                or row["reply_outcomes"]["valid"] != row["valid_reply_events"]):
            raise ValueError("Replay exclusive reply outcomes do not conserve comments")
    months = actual["actual_months"]
    if [g["month"] for g in graphs["months"]] != months or [d["month"] for d in detection["months"]] != months:
        raise ValueError("Replay monthly summaries do not match the cohort")
    for graph, result in zip(graphs["months"], detection["months"]):
        batch = [r for r in cells if r["month"] == graph["month"]]
        canonical = next(r for r in result["runs"] if r["seed"] == detection["canonical_seed"])
        if (sum(r["valid_reply_events"] for r in batch) != graph["reply_events"]
                or sum(r["comments"] for r in batch) != graph["comment_records"]
                or canonical["assigned_users"] != graph["reply_endpoints"]
                or sum(canonical["sizes"]) != canonical["assigned_users"]
                or result["graph_sha256"] != graph["graph_sha256"]):
            raise ValueError("Replay monthly totals or partition support mismatch")
        # Plotting reads R and canonical memberships: both must be covered by the
        # manifest, not merely present on disk beside some unrelated hashed file.
        hashed_graphs = {Path(p) for p in manifests["graphs"]["artifact_hashes"]}
        hashed_detection = {Path(p) for p in manifests["detection"]["artifact_hashes"]}
        if (Path("snapshots") / graph["month"] / "R.csv" not in hashed_graphs
                or Path("memberships") / graph["month"] / f"membership-seed{detection['canonical_seed']}.csv" not in hashed_detection):
            raise ValueError("Replay plotted graph/membership must have declared artifact hashes")
    return {"runs": runs, "manifests": manifests, "normalization": normalization,
            "graphs": graphs, "detection": detection,
            "corpora": read_json(runs["normalized"] / "corpus_manifest.json")}


def read_csv(path: Path) -> list[dict]:
    """Read a small aggregate graph/membership table, never raw corpus JSONL."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
