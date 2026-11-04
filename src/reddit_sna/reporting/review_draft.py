"""Create a clearly disclosed AI-assisted draft from an automated assessment.

The output is deliberately *not* a human submission.  A reviewer must still
adopt or change every judgment and record the actual submission time before
sending a form to the coordinator.
"""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


LABELS = frozenset({'stable', 'grow', 'shrink', 'merge', 'split', 'dissolve', 'unresolved'})
CONFIDENCE = frozenset({'low', 'medium', 'high'})
WORKSHEET_FIELDS = ('case_id', 'label', 'confidence', 'rationale')


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _load_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def _validate_blank_worksheet(rows, fieldnames):
    if tuple(fieldnames or ()) != WORKSHEET_FIELDS:
        raise ValueError(f'Worksheet must use exactly these columns: {WORKSHEET_FIELDS}')
    identifiers = [row['case_id'].strip() for row in rows]
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError('Worksheet needs one non-duplicated case_id per row')
    if any(row['label'].strip() or row['confidence'].strip() or row['rationale'].strip() for row in rows):
        raise ValueError('Source worksheet is not blank; preserve real reviewer work separately')


def _validate_automated_rows(rows):
    identifiers = []
    for row in rows:
        case_id = row.get('case_id', '').strip()
        label = row.get('label', '').strip()
        confidence = row.get('confidence', '').strip()
        rationale = row.get('rationale', '').strip()
        if not case_id or label not in LABELS or confidence not in CONFIDENCE or not rationale:
            raise ValueError(f'Invalid automated assessment row: {case_id or "missing case_id"}')
        if row.get('reviewer_type', '').strip() != 'automated':
            raise ValueError('Automated source must declare reviewer_type=automated')
        identifiers.append(case_id)
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise ValueError('Automated source needs one non-duplicated case_id per row')


def create_ai_assisted_draft(blank_worksheet, automated_assessment, output, reviewer_id,
                             guidance_version='frozen_v1.1'):
    """Write a non-submitted reviewer-form draft and provenance metadata.

    `output` must not exist. This avoids silently replacing a previous draft or
    any genuine reviewer submission.
    """
    blank_worksheet = Path(blank_worksheet).resolve()
    automated_assessment = Path(automated_assessment).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')

    worksheet_fields, worksheet_rows = _load_csv(blank_worksheet)
    automated_fields, automated_rows = _load_csv(automated_assessment)
    _validate_blank_worksheet(worksheet_rows, worksheet_fields)
    _validate_automated_rows(automated_rows)
    if not set(WORKSHEET_FIELDS).issubset(automated_fields or ()):
        raise ValueError('Automated source lacks reviewer worksheet fields')

    automated_by_case = {row['case_id'].strip(): row for row in automated_rows}
    worksheet_ids = [row['case_id'].strip() for row in worksheet_rows]
    if set(worksheet_ids) != set(automated_by_case):
        raise ValueError('Automated source and blank worksheet have different case sets')

    output.mkdir(parents=True, exist_ok=False)
    draft_rows = [
        {field: automated_by_case[case_id][field].strip() for field in WORKSHEET_FIELDS}
        for case_id in worksheet_ids
    ]
    draft_path = output / 'reviewer_1.csv'
    with draft_path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=WORKSHEET_FIELDS)
        writer.writeheader()
        writer.writerows(draft_rows)

    metadata = {
        'status': 'unsubmitted_ai_assisted_draft',
        'reviewer_id': reviewer_id,
        'reviewer_role': 'reviewer_1',
        'guidance_version': guidance_version,
        'drafted_utc': datetime.now(timezone.utc).isoformat(),
        'cases': len(draft_rows),
        'human_judgments_claimed': 0,
        'ai_assistance_seen': True,
        'disclosure': (
            'This CSV was copied from a separate automated assessment. It is not a human '
            'reviewer submission and must not be sent as one until the named reviewer adopts '
            'or changes every row and records the real submission time.'
        ),
        'original_blank_worksheet_sha256': _sha256(blank_worksheet),
        'automated_source_sha256': _sha256(automated_assessment),
        'draft_sha256': _sha256(draft_path),
        'machine_labels_seen_before_draft': False,
        'coverage_snapshot_seen_before_draft': False,
        'reviewer_2_labels_seen_before_draft': False,
        'actual_submitted_at_utc': None,
        'requires_reviewer_attestation': True,
    }
    metadata_path = output / 'submission-metadata.json'
    with metadata_path.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

    readme = '''# Bản nháp reviewer 1 có hỗ trợ AI

Đây là bản nháp được tạo từ một đánh giá tự động. Nó **không phải** phiếu người
chấm và chưa được nộp cho điều phối.

Trước khi nộp, reviewer phải tự đọc và chấp nhận hoặc sửa từng dòng trong
`reviewer_1.csv`, ghi thời điểm nộp thật trong metadata, và khai báo đã xem hỗ
trợ AI. Không chia sẻ file này cho reviewer 2 trước khi hai phiếu đã khóa.
'''
    (output / 'README.md').write_text(readme, encoding='utf-8')
    return metadata


def create_submission_ready_package(draft_directory, output, reviewer_id, adoption_note):
    """Copy an adopted AI-assisted draft into a coordinator-ready package.

    This function cannot convert automated work into unassisted human agreement.
    It preserves that limitation in the package metadata and leaves the actual
    send/receipt timestamps for the reviewer and coordinator to record.
    """
    draft_directory = Path(draft_directory).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    if not adoption_note.strip():
        raise ValueError('An explicit reviewer adoption note is required')

    draft_csv = draft_directory / 'reviewer_1.csv'
    draft_metadata_path = draft_directory / 'submission-metadata.json'
    draft_fields, draft_rows = _load_csv(draft_csv)
    _validate_automated_rows([
        {**row, 'reviewer_type': 'automated'} for row in draft_rows
    ])
    if tuple(draft_fields or ()) != WORKSHEET_FIELDS:
        raise ValueError(f'Draft must use exactly these columns: {WORKSHEET_FIELDS}')
    draft_metadata = json.loads(draft_metadata_path.read_text(encoding='utf-8'))
    if draft_metadata.get('status') != 'unsubmitted_ai_assisted_draft':
        raise ValueError('Only an explicitly unsubmitted AI-assisted draft may be finalized')
    if draft_metadata.get('cases') != len(draft_rows):
        raise ValueError('Draft metadata case count does not match its CSV')

    output.mkdir(parents=True, exist_ok=False)
    reviewer_csv = output / 'reviewer_1.csv'
    shutil.copy2(draft_csv, reviewer_csv)
    prepared_utc = datetime.now(timezone.utc).isoformat()
    metadata = {
        'status': 'reviewer_adopted_ai_assisted_submission_ready',
        'reviewer_id': reviewer_id,
        'reviewer_role': 'reviewer_1',
        'prepared_utc': prepared_utc,
        'actual_submitted_at_utc': None,
        'coordinator_receipt_utc': None,
        'cases': len(draft_rows),
        'guidance_version': draft_metadata['guidance_version'],
        'reviewer_adoption_note': adoption_note.strip(),
        'ai_assistance_seen': True,
        'submission_provenance': (
            'The reviewer explicitly adopted an AI-assisted draft. The automated '
            'source remains preserved separately and this package must not be '
            'reported as unassisted human annotation.'
        ),
        'human_judgments_claimed': 0,
        'eligible_for_unassisted_human_agreement': False,
        'eligible_for_technical_comparison_if_coordinator_accepts': True,
        'machine_labels_seen_before_submission': False,
        'coverage_snapshot_seen_before_submission': False,
        'reviewer_2_labels_seen_before_submission': False,
        'source_draft_sha256': _sha256(draft_csv),
        'source_draft_metadata_sha256': _sha256(draft_metadata_path),
        'reviewer_1_sha256': _sha256(reviewer_csv),
        'requires_reviewer_send_time': True,
        'requires_coordinator_checksum_and_receipt': True,
    }
    metadata_path = output / 'submission-metadata.json'
    with metadata_path.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    readme = '''# Reviewer 1 submission-ready package

This package is ready to be sent directly to the coordinator. The reviewer
explicitly adopted an AI-assisted draft and the metadata discloses that fact.
It is not an unassisted human-annotation submission and cannot be used to claim
unassisted human agreement.

Before sending, the reviewer records the actual send time in their message to
the coordinator. The coordinator preserves this package, computes/records its
checksum and receipt time, and only then releases both reviewer forms for any
agreement procedure.
'''
    readme_path = output / 'README.md'
    readme_path.write_text(readme, encoding='utf-8')
    checksum_path = output / 'SHA256SUMS.txt'
    checksum_path.write_text('\n'.join(
        f'{_sha256(path)}  {path.name}'
        for path in (reviewer_csv, metadata_path, readme_path)
    ) + '\n', encoding='utf-8')
    archive_path = output / 'reviewer_1_submission_ready.zip'
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (reviewer_csv, metadata_path, readme_path, checksum_path):
            archive.write(path, arcname=path.name)
    return {
        **metadata,
        'archive_sha256': _sha256(archive_path),
        'archive_path': str(archive_path),
    }
