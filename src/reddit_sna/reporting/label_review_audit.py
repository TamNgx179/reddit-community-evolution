"""Audit a blinded ``review-labels`` packet without revealing tracker labels.

The audit consumes coordinator material only to prove that IDs and hashes match.
Its outputs deliberately omit tracker labels, reasons, predictions and raw IDs,
so they can accompany a reviewer handoff.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re

from reddit_sna.data.archive import digest_file


CASE_FIELDS = frozenset({
    "case_id", "feature_month", "label_month", "focal_source", "current_groups",
    "next_overlapping_groups", "evidence_scope",
})
FORM_FIELDS = ("case_id", "reviewer", "human_label", "confidence", "rationale")
TOKEN = re.compile(r"^[0-9a-f]{20}$")
SOURCE_ID = re.compile(r"^source-[0-9]+$")
TARGET_ID = re.compile(r"^target-[0-9]+$")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def _write_csv(path: Path, rows):
    fields = ("case_id", "source_groups", "source_members", "successor_groups",
              "successor_members", "evidence_scope_ok")
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _check_group_map(groups, identifier, case_id):
    if not isinstance(groups, dict) or not groups:
        raise ValueError(f"{case_id}: expected nonempty group evidence")
    member_count = 0
    for group_id, members in groups.items():
        if not identifier.fullmatch(group_id) or not isinstance(members, list) or not members:
            raise ValueError(f"{case_id}: invalid blinded group evidence")
        if any(not isinstance(token, str) or not TOKEN.fullmatch(token) for token in members):
            raise ValueError(f"{case_id}: member token leaks or has an invalid format")
        member_count += len(members)
    return member_count


def audit_label_review_packet(packet, output):
    """Validate a prepared packet and write safe evidence inventory to new output."""
    packet, output = Path(packet).resolve(), Path(output).resolve()
    if output.exists() or output == packet or output.is_relative_to(packet) or packet.is_relative_to(output):
        raise ValueError("Use a new audit output separate from the packet")
    cases_path = packet / "reviewer/cases.json"
    forms_path = packet / "reviewer/annotations.csv"
    key_path = packet / "coordinator/answer_key.json"
    manifest_path = packet / "manifest.json"
    for path in (cases_path, forms_path, key_path, manifest_path):
        if not path.is_file():
            raise ValueError(f"Missing review packet file: {path.relative_to(packet)}")
    manifest = _load_json(manifest_path)
    if manifest.get("status") != "prepared_pending_human_annotation":
        raise ValueError("Packet is not a prepared blank review packet")
    expected_hashes = manifest.get("artifact_hashes", {})
    for relative in ("reviewer/cases.json", "reviewer/annotations.csv", "coordinator/answer_key.json"):
        if expected_hashes.get(relative) != digest_file(packet / relative):
            raise ValueError(f"Packet artifact hash differs: {relative}")

    cases = _load_json(cases_path)
    answers = _load_json(key_path)
    if not isinstance(cases, list) or not cases:
        raise ValueError("Packet has no blinded cases")
    if not isinstance(answers, list):
        raise ValueError("Coordinator key must be a list")
    case_ids, safe_rows = [], []
    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            raise ValueError("Case has missing or leaked top-level fields")
        case_id = case["case_id"]
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError("Case IDs must be nonempty and unique")
        if case["focal_source"] != "source-0":
            raise ValueError(f"{case_id}: focal source must be source-0")
        current = case["current_groups"]
        if "source-0" not in current:
            raise ValueError(f"{case_id}: current evidence lacks source-0")
        source_members = _check_group_map(current, SOURCE_ID, case_id)
        successors = case["next_overlapping_groups"]
        if not isinstance(successors, dict):
            raise ValueError(f"{case_id}: successor evidence must be a map")
        successor_members = 0
        for target_id, members in successors.items():
            if not TARGET_ID.fullmatch(target_id) or not isinstance(members, list) or not members:
                raise ValueError(f"{case_id}: invalid blinded successor evidence")
            if any(not isinstance(token, str) or not TOKEN.fullmatch(token) for token in members):
                raise ValueError(f"{case_id}: successor token leaks or has an invalid format")
            successor_members += len(members)
        scope_ok = isinstance(case["evidence_scope"], str) and "Observed reply-network" in case["evidence_scope"]
        if not scope_ok:
            raise ValueError(f"{case_id}: missing observed-network scope statement")
        case_ids.append(case_id)
        safe_rows.append(dict(case_id=case_id, source_groups=len(current), source_members=source_members,
                              successor_groups=len(successors), successor_members=successor_members,
                              evidence_scope_ok=True))

    answer_ids = [row.get("case_id") for row in answers if isinstance(row, dict)]
    if len(answer_ids) != len(answers) or set(answer_ids) != set(case_ids) or len(set(answer_ids)) != len(answer_ids):
        raise ValueError("Coordinator key IDs do not match blinded case IDs")
    with forms_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FORM_FIELDS:
            raise ValueError("Annotation CSV has unexpected fields")
        forms = list(reader)
    if len(forms) != 2 * len(case_ids):
        raise ValueError("Need one blank row per reviewer and case")
    for reviewer in ("reviewer_a", "reviewer_b"):
        rows = [row for row in forms if row["reviewer"] == reviewer]
        if [row["case_id"] for row in rows] != case_ids:
            raise ValueError(f"{reviewer}: case IDs/order differ from blinded packet")
        if any(row["human_label"] or row["confidence"] or row["rationale"] for row in rows):
            raise ValueError(f"{reviewer}: prepared form is not blank")
    if any(row["reviewer"] not in {"reviewer_a", "reviewer_b"} for row in forms):
        raise ValueError("Annotation CSV has an unexpected reviewer role")

    output.mkdir(parents=True, exist_ok=False)
    _write_csv(output / "case-evidence-check.csv", safe_rows)
    summary = dict(
        status="blinded_packet_verified",
        cases=len(case_ids),
        reviewers={"reviewer_a": len(case_ids), "reviewer_b": len(case_ids)},
        empty_successor_cases=sum(not row["successor_groups"] for row in safe_rows),
        source_packet_sha256={
            "reviewer/cases.json": digest_file(cases_path),
            "reviewer/annotations.csv": digest_file(forms_path),
            "coordinator/answer_key.json": digest_file(key_path),
            "manifest.json": digest_file(manifest_path),
        },
        limitations=(
            "Verified file structure, blinded field set and token format only. "
            "It does not certify social ground truth, reviewer independence or annotation completion."
        ),
    )
    _write_json(output / "summary.json", summary)
    _write_json(output / "manifest.json", dict(
        status="complete", stage="blinded-label-review-audit",
        artifact_hashes={path.name: digest_file(path) for path in sorted(output.iterdir()) if path.is_file()},
    ))
    return summary
