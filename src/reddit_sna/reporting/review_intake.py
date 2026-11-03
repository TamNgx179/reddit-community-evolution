"""Prepare a private reviewer workspace without choosing any human judgments."""

import csv
from datetime import datetime, timezone
import gzip
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from reddit_sna.data.archive import digest_file

BLOCKED_PARTS = ('coordinator', 'answer_key', 'answer-key', 'answers.json', 'followup',
                 'follow-up', 'predictions', 'reviewer_2', 'reviewer-2', 'assessment_2')
BLOCKED_FIELDS = {'label', 'machine_label', 'machine_event', 'y_true', 'y_pred',
                  'prediction', 'predictions', 'threshold', 'alpha', 'beta',
                  'stratum', 'sampling_stratum', 'answer_key', 'source_mapping'}
ALLOWED_SUFFIXES = {'.html', '.csv', '.json', '.gz', '.png', '.svg', '.css', '.md', '.txt', '.sha256'}


def _check_fields(value, case_ids):
    if isinstance(value, dict):
        if set(value) & BLOCKED_FIELDS:
            raise ValueError('Case payload contains a machine-answer/threshold/stratum field')
        if isinstance(value.get('case_id'), str):
            case_ids.add(value['case_id'])
        for child in value.values():
            _check_fields(child, case_ids)
    elif isinstance(value, list):
        for child in value:
            _check_fields(child, case_ids)


def prepare_reviewer_workspace(archive, output, phase, reviewer_id, *, expected_sha256=None):
    """Copy only an isolated reviewer-1 archive and leave all decisions blank.

    This is technical intake, not human receipt/annotation or a guarantee of
    comprehensive blinding. No key is opened, no labels are inferred, and no
    agreement is calculated. Raw ZIP bytes remain available as source evidence.
    """
    archive, output = Path(archive).resolve(), Path(output).resolve()
    if phase not in ('pilot', 'main') or not reviewer_id.strip():
        raise ValueError('Use pilot/main and an actual reviewer identifier')
    if output.exists() or archive.is_relative_to(output):
        raise ValueError('Use a new private output directory outside its input')
    original_hash = digest_file(archive)
    if expected_sha256 and original_hash != expected_sha256:
        raise ValueError('Archive SHA-256 differs from the coordinator handoff')
    expected_count = 6 if phase == 'pilot' else 60
    with zipfile.ZipFile(archive) as zipped:
        names, folded_names, total = set(), set(), 0
        for entry in zipped.infolist():
            name = entry.filename
            part = PurePosixPath(name)
            if (name.casefold() in folded_names or part.is_absolute() or '..' in part.parts or '\\' in name
                    or ':' in name or any(token in name.lower() for token in BLOCKED_PARTS)
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Unsafe, duplicate or non-reviewer archive entry')
            names.add(name)
            folded_names.add(name.casefold())
            total += entry.file_size
            if not entry.is_dir() and part.suffix.lower() not in ALLOWED_SUFFIXES:
                raise ValueError('Unexpected file type in reviewer evidence archive')
        if total > 1024**3:
            raise ValueError('Review package exceeds the 1 GiB intake limit')
        forms = [n for n in names if PurePosixPath(n).name in ('annotations.csv', 'reviewer_1.csv', 'assessment_1.csv')]
        indexes = [n for n in names if PurePosixPath(n).name == 'index.html']
        if len(forms) != 1 or not indexes:
            raise ValueError('Need one reviewer worksheet and an HTML index')
        if zipped.testzip() is not None:
            raise ValueError('Reviewer ZIP failed CRC verification')
        reader = csv.DictReader(io.StringIO(zipped.read(forms[0]).decode('utf-8-sig')))
        fields, rows = reader.fieldnames, list(reader)
        label_fields = [field for field in ('label', 'human_label') if field in (fields or [])]
        if (len(label_fields) != 1 or len(set(fields or [])) != len(fields or [])
                or not {'case_id', 'confidence', 'rationale'} <= set(fields or [])
                or len(rows) != expected_count or len({r['case_id'] for r in rows}) != expected_count
                or any(None in row or any(value is None for value in row.values())
                       or not row['case_id'].strip() for row in rows)):
            raise ValueError('Reviewer worksheet case inventory/schema differs from the phase')
        label_field = label_fields[0]
        if any(row[field].strip() for row in rows for field in (label_field, 'confidence', 'rationale')):
            raise ValueError('Intake requires blank original judgments; preserve any actual submissions separately')
        payload_count, evidence_case_ids = 0, set()
        for entry in zipped.infolist():
            if entry.is_dir() or entry.filename == forms[0]:
                continue
            suffix = PurePosixPath(entry.filename).suffix.lower()
            if suffix not in ('.json', '.gz'):
                continue
            content = zipped.read(entry)
            if suffix == '.gz':
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as compressed:
                    content = compressed.read(64*1024**2 + 1)
                if len(content) > 64*1024**2:
                    raise ValueError('Compressed case exceeds the 64 MiB inspection limit')
            payload = json.loads(content.decode('utf-8-sig'))
            _check_fields(payload, evidence_case_ids)
            payload_count += 1
        if not {row['case_id'] for row in rows} <= evidence_case_ids:
            raise ValueError('Some worksheet cases have no machine-readable case evidence')
        if digest_file(archive) != original_hash:
            raise ValueError('Input archive changed during inspection')
        output.mkdir(parents=True, exist_ok=False)
        originals = output/'packet'
        originals.mkdir()
        for entry in zipped.infolist():
            destination = originals.joinpath(*PurePosixPath(entry.filename).parts)
            if not destination.resolve().is_relative_to(originals):
                raise ValueError('Archive entry escapes private workspace')
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(zipped.read(entry))
        (output/'annotations-working.csv').write_bytes(zipped.read(forms[0]))
    checklist = [dict(case_id=row['case_id'], full_membership_read='', all_predecessors_successors_read='',
                      incident_edges_read='', observation_coverage_read='', missing_evidence='', notes='')
                 for row in rows]
    with (output/'evidence-checklist.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checklist[0]))
        writer.writeheader()
        writer.writerows(checklist)
    status = dict(status='prepared_pending_human_annotation', phase=phase, reviewer_id=reviewer_id,
        cases=expected_count, annotated=0, main_validation_cases=0,
        technical_intake_utc=datetime.now(timezone.utc).isoformat(),
        human_receipt_confirmed=False, rubric_frozen=False,
        archive_sha256=original_hash, coordinator_hash_compared=bool(expected_sha256),
        payload_files_checked=payload_count, index_files=['packet/'+n for n in sorted(indexes)],
        original_worksheet='packet/'+forms[0], working_worksheet='annotations-working.csv',
        limitation='File/field checks cannot certify every display is fully blinded or evidence complete. '
                   'Human review, receipt, rubric approval and submission times must be recorded truthfully.')
    with (output/'intake.json').open('x', encoding='utf-8') as stream:
        json.dump(status, stream, indent=2)
        stream.write('\n')
    return status
