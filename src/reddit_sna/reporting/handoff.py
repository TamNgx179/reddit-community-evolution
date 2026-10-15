"""Independent consumer of public preparation files, without producer imports.

This is an interface acceptance check, not evidence that a partner has reviewed
the files or that a tracker/predictor is implemented. Only aggregate results are
returned; pseudonymous memberships stay in local artifacts.
"""

import csv
import hashlib
import json
import math
import re
from pathlib import Path


def _table(path: Path, columns: list[str]) -> list[dict]:
    """Require an exact CSV contract rather than silently dropping unknown fields."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != columns:
            raise ValueError(f"Handoff CSV schema mismatch: {path.name}")
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("Handoff CSV row width mismatch")
        return rows


def _hash(path: Path) -> str:
    """Use an independent streaming SHA-256 implementation in the consumer."""
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inspect_handoff(graph_run: Path, detection_run: Path, artifact_root: Path) -> dict:
    """Validate files a tracker would consume and return aggregate acceptance.

    Verify completed manifests, every declared hash, source linkage, actual
    months, identity/cohort and canonical membership keys. Assigned users must
    equal R endpoints, while users.csv also retains isolates. No producer API,
    graph library, partner output or raw identity mapping is needed.
    """
    manifests = []
    for run in (graph_run, detection_run):
        run = run.resolve()
        if not run.is_relative_to(artifact_root.resolve()):
            raise ValueError("Handoff source outside artifacts")
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") not in {"complete", "complete_through_detection"}:
            raise ValueError("Handoff source is not complete")
        hashes = manifest.get("artifact_hashes", {})
        if not hashes:
            raise ValueError("Handoff source lacks hashes")
        for relative, expected in hashes.items():
            path = (run / relative).resolve()
            if not path.is_relative_to(run) or _hash(path) != expected:
                raise ValueError("Handoff artifact hash mismatch or unsafe path")
        manifests.append(manifest)
    gm, dm = manifests
    if ("snapshots.json" not in gm["artifact_hashes"] or "detection.json" not in dm["artifact_hashes"]):
        raise ValueError("Handoff summary missing from hash inventory")
    if graph_run.resolve() != detection_run.resolve():
        if (Path(dm.get("source_run", "")).resolve() != graph_run.resolve()
                or dm.get("source_manifest_sha256") != _hash(graph_run / "manifest.json")):
            raise ValueError("Handoff source linkage mismatch")
    graph = json.loads((graph_run / "snapshots.json").read_text(encoding="utf-8"))
    detection = json.loads((detection_run / "detection.json").read_text(encoding="utf-8"))
    for field in ("actual_months", "graph_reference", "start_month", "end_month_exclusive"):
        if not (graph[field] == detection[field] == dm[field]):
            raise ValueError(f"Handoff period/reference mismatch: {field}")
    if graph["identity_scope"] != dm["identity_scope"]:
        raise ValueError("Handoff identity mismatch")
    months = graph["actual_months"]
    if not months or months != sorted(set(months)) or [r["month"] for r in graph["months"]] != months:
        raise ValueError("Handoff invalid month sequence")
    if [r["month"] for r in detection["months"]] != months:
        raise ValueError("Handoff monthly summaries mismatch")
    accepted, references = [], set()
    for month, summary in zip(months, detection["months"]):
        canonical = next(r for r in summary["runs"] if r["seed"] == detection["canonical_seed"])
        relative = f"memberships/{month}/membership-seed{detection['canonical_seed']}.csv"
        required_graph = [f"snapshots/{month}/{name}" for name in ("R.csv", "users.csv", "directed_R.csv")]
        if graph["graph_protocol"] == "reply-r-v3-order1":
            required_graph.append(f"snapshots/{month}/node_order.csv")
        if (relative not in {Path(p).as_posix() for p in dm["artifact_hashes"]}
                or not set(required_graph).issubset({Path(p).as_posix() for p in gm["artifact_hashes"]})):
            raise ValueError("Handoff public input missing from hash inventory")
        memberships = _table(detection_run / relative, ["reference_id", "month", "community_id", "user_id"])
        users = _table(graph_run / "snapshots" / month / "users.csv", ["user_id", "authored_in_month", "has_reply_edge"])
        edges = _table(graph_run / "snapshots" / month / "R.csv", ["month", "source_user_id", "target_user_id", "weight"])
        seen = set()
        for edge in edges:
            pair = tuple(sorted((edge["source_user_id"], edge["target_user_id"])))
            weight = float(edge["weight"])
            if (edge["month"] != month or not all(pair) or pair[0] == pair[1] or pair in seen
                    or not math.isfinite(weight) or weight <= 0):
                raise ValueError("Handoff invalid R edge")
            seen.add(pair)
        endpoints = {r[k] for r in edges for k in ("source_user_id", "target_user_id")}
        if graph["graph_protocol"] == "reply-r-v3-order1":
            order = _table(graph_run / "snapshots" / month / "node_order.csv", ["month","user_id","order_key"])
            if (len(order) != len(endpoints) or {r["user_id"] for r in order} != endpoints
                    or len({r["order_key"] for r in order}) != len(order)
                    or any(r["month"] != month or not re.fullmatch(r"[0-9a-f]{64}",r["order_key"]) for r in order)):
                raise ValueError("Handoff invalid causal node ordering")
        assigned = [r["user_id"] for r in memberships]
        if len(assigned) != len(set(assigned)):
            raise ValueError("Handoff duplicate membership user key")
        if set(assigned) != endpoints or canonical["assigned_users"] != len(endpoints):
            raise ValueError("Handoff membership/endpoint mismatch")
        if any(r["month"] != month or r["reference_id"] != canonical["reference_id"]
               or not r["community_id"].strip() or not r["user_id"].strip() for r in memberships):
            raise ValueError("Handoff invalid membership month/reference/key")
        if len({r["user_id"] for r in users}) != len(users):
            raise ValueError("Handoff duplicate observed user")
        if any(r["authored_in_month"] not in {"0", "1"} or r["has_reply_edge"] not in {"0", "1"} for r in users):
            raise ValueError("Handoff invalid user flags")
        if {r["user_id"] for r in users if r["has_reply_edge"] == "1"} != endpoints:
            raise ValueError("Handoff users.csv endpoint flags mismatch")
        references.add(canonical["reference_id"])
        accepted.append({"month": month, "assigned_users": len(assigned),
                         "observed_users": len(users), "communities": len({r['community_id'] for r in memberships})})
    if len(references) != 1:
        raise ValueError("Handoff canonical reference must be shared across cohort months")
    return {"status": "accepted_by_automated_consumer", "partner_acceptance": "not_verified",
            "identity_scope": graph["identity_scope"], "graph_reference": graph["graph_reference"],
            "canonical_reference": next(iter(references)), "months": accepted,
            "transition_opportunities": max(0, len(months)-1),
            "forecast_readiness": "label support and temporal split require downstream validation"}
