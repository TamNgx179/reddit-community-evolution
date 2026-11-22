"""Create role-isolated handoffs from a blinded ``review-labels`` packet."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import zipfile

from reddit_sna.data.archive import digest_file


FORM_FIELDS = ("case_id", "reviewer", "human_label", "confidence", "rationale")
REVIEWERS = frozenset({"reviewer_a", "reviewer_b"})
PACKET_ARTIFACTS = (
    "reviewer/cases.json",
    "reviewer/annotations.csv",
    "coordinator/answer_key.json",
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_forms(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FORM_FIELDS:
            raise ValueError("Annotation CSV has unexpected fields")
        return list(reader)


def _write_json(path: Path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def _write_forms(path: Path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FORM_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_checksums(output: Path, files):
    sums = output / "SHA256SUMS.txt"
    with sums.open("x", encoding="utf-8") as stream:
        for path in files:
            stream.write(f"{digest_file(path)}  {path.relative_to(output).as_posix()}\n")
    return sums


def _zip(output: Path, archive_name: str, files):
    archive_path = output / archive_name
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(output).as_posix())
    return archive_path


def package_label_review_handoff(packet, output, role):
    """Create a new role-isolated reviewer or coordinator handoff directory.

    Reviewer handoffs contain only blinded evidence and their own blank form.
    Coordinator handoffs contain only the answer key and manifest. No existing
    packet or output may be overwritten.
    """
    packet, output = Path(packet).resolve(), Path(output).resolve()
    if role not in REVIEWERS | {"coordinator"}:
        raise ValueError("Role must be reviewer_a, reviewer_b or coordinator")
    if output.exists() or output == packet or output.is_relative_to(packet) or packet.is_relative_to(output):
        raise ValueError("Use a new handoff output separate from the packet")
    cases_path = packet / "reviewer/cases.json"
    forms_path = packet / "reviewer/annotations.csv"
    key_path = packet / "coordinator/answer_key.json"
    manifest_path = packet / "manifest.json"
    for path in (cases_path, forms_path, key_path, manifest_path):
        if not path.is_file():
            raise ValueError(f"Missing source packet file: {path.relative_to(packet)}")
    manifest = _load_json(manifest_path)
    if manifest.get("status") != "prepared_pending_human_annotation":
        raise ValueError("Source packet is not a prepared blank review packet")
    expected_hashes = manifest.get("artifact_hashes", {})
    for relative in PACKET_ARTIFACTS:
        if expected_hashes.get(relative) != digest_file(packet / relative):
            raise ValueError(f"Source packet artifact hash differs: {relative}")
    cases = _load_json(cases_path)
    case_ids = [row.get("case_id") for row in cases if isinstance(row, dict)]
    if not case_ids or len(case_ids) != len(cases) or len(set(case_ids)) != len(case_ids):
        raise ValueError("Source cases must have unique IDs")
    forms = _load_forms(forms_path)
    if any(row["human_label"] or row["confidence"] or row["rationale"] for row in forms):
        raise ValueError("Source annotations are not blank")

    output.mkdir(parents=True, exist_ok=False)
    if role == "coordinator":
        coordinator = output / "coordinator"
        coordinator.mkdir()
        key_copy = coordinator / "answer_key.json"
        manifest_copy = coordinator / "packet-manifest.json"
        shutil.copy2(key_path, key_copy)
        shutil.copy2(manifest_path, manifest_copy)
        intake = dict(
            status="coordinator_handoff_prepared",
            role=role,
            cases=len(case_ids),
            source_packet_sha256={
                "coordinator/answer_key.json": digest_file(key_path),
                "manifest.json": digest_file(manifest_path),
            },
            handling=(
                "Keep this key separate from both reviewers. Record receipt time and hashes "
                "for reviewer submissions before releasing the key for agreement."
            ),
        )
        _write_json(output / "intake.json", intake)
        readme = """# Coordinator handoff\n\nThis directory contains the tracker answer key and packet manifest. Do not forward it\nto reviewer A or reviewer B. Preserve the original files, record their hashes and\nreceipt time, and reveal them only after both reviewer submissions are locked.\n"""
        (output / "README.md").write_text(readme, encoding="utf-8")
        files = [key_copy, manifest_copy, output / "intake.json", output / "README.md"]
        sums = _write_checksums(output, files)
        archive = _zip(output, "coordinator_handoff.zip", files + [sums])
        return dict(**intake, archive=str(archive), archive_sha256=digest_file(archive))

    role_rows = [row for row in forms if row["reviewer"] == role]
    if [row["case_id"] for row in role_rows] != case_ids:
        raise ValueError(f"{role}: form IDs/order differ from blinded cases")
    reviewer = output / "reviewer"
    reviewer.mkdir()
    cases_copy = reviewer / "cases.json"
    form_copy = reviewer / f"{role}.csv"
    shutil.copy2(cases_path, cases_copy)
    _write_forms(form_copy, role_rows)
    intake = dict(
        status="reviewer_handoff_prepared",
        role=role,
        cases=len(case_ids),
        source_packet_sha256={
            "reviewer/cases.json": digest_file(cases_path),
            "reviewer/annotations.csv": digest_file(forms_path),
            "manifest.json": digest_file(manifest_path),
        },
        delivered_sha256={
            "reviewer/cases.json": digest_file(cases_copy),
            f"reviewer/{role}.csv": digest_file(form_copy),
        },
        excluded_from_reviewer_handoff=["coordinator/answer_key.json", "manifest.json", "other reviewer form"],
        annotation_status="blank_pending_independent_annotation",
    )
    _write_json(output / "intake.json", intake)
    provenance = f"""# Provenance declaration — {role}

- Reviewer identity:
- Rubric/version used: frozen_v1.1 only after coordinator confirmation
- Did you use AI assistance? yes/no
- If yes, describe exactly what was used and keep suggestions separate from the final decision.
- Answer key, tracker label/reason and model predictions seen before locking? yes/no
- Other reviewer form or case decisions seen before locking? yes/no
- Actual submission time with timezone:

Do not change `reviewer/{role}.csv` after sending its hash to the coordinator.
"""
    (output / "provenance.md").write_text(provenance, encoding="utf-8")
    readme = f"""# Blinded review handoff — {role}

This handoff contains {len(case_ids)} blinded membership-evidence cases and one blank form for
{role}. It deliberately excludes the tracker answer key, packet manifest and the
other reviewer form. Work independently under the agreed rubric. Record one event
label, confidence and evidence-based rationale for each case, then send the final
CSV and SHA-256 to the coordinator. A target with no overlapping member is valid
observed evidence, not proof of social dissolution.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    files = [cases_copy, form_copy, output / "intake.json", output / "provenance.md", output / "README.md"]
    sums = _write_checksums(output, files)
    archive = _zip(output, f"{role}_handoff.zip", files + [sums])
    return dict(**intake, archive=str(archive), archive_sha256=digest_file(archive))
