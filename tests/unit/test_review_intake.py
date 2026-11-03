"""Blinded recipient intake must not fabricate judgments or expose a key."""

import csv
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from reddit_sna.data.archive import digest_file
from reddit_sna.reporting.review_intake import prepare_reviewer_workspace


def reviewer_fixture(archive, *, count=6, extra=None, judgment='', evidence=None):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=['case_id', 'reviewer', 'human_label', 'confidence', 'rationale'])
    writer.writeheader()
    for index in range(count):
        writer.writerow(dict(case_id=f'fixture-{index}', reviewer='reviewer_1',
                             human_label=judgment, confidence='', rationale=''))
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('index.html', '<a href="cases/fixture.json.gz">Fixture evidence</a>')
        zipped.writestr('annotations.csv', buffer.getvalue())
        for index in range(count):
            zipped.writestr(f'cases/fixture-{index}.json.gz', gzip.compress(json.dumps(
                evidence or dict(case_id=f'fixture-{index}', current_groups={'source-0': ['a', 'b']},
                                 next_groups={'target-0': ['a', 'b']})).encode()))
        if extra:
            zipped.writestr(*extra)


class ReviewerIntakeTests(unittest.TestCase):
    def test_preserves_original_and_prepares_only_blank_working_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root/'pilot-reviewer_1.zip'
            reviewer_fixture(archive)
            expected = digest_file(archive)
            result = prepare_reviewer_workspace(archive, root/'out', 'pilot', 'fixture-reviewer',
                                                expected_sha256=expected)
            self.assertEqual(result['cases'], 6)
            self.assertEqual(result['annotated'], 0)
            self.assertEqual(result['main_validation_cases'], 0)
            self.assertFalse(result['human_receipt_confirmed'])
            self.assertEqual(digest_file(archive), expected)
            self.assertEqual((root/'out/annotations-working.csv').read_bytes(),
                             (root/'out/packet/annotations.csv').read_bytes())
            with self.assertRaises(ValueError):
                prepare_reviewer_workspace(archive, root/'out', 'pilot', 'fixture-reviewer')

    def test_wrong_phase_hash_or_existing_judgments_are_rejected(self):
        for option in ('phase', 'hash', 'judgment'):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root/'pilot.zip'
                reviewer_fixture(archive, judgment='grow' if option == 'judgment' else '')
                with self.assertRaises(ValueError):
                    prepare_reviewer_workspace(archive, root/'out', 'main' if option == 'phase' else 'pilot',
                        'fixture-reviewer', expected_sha256='0'*64 if option == 'hash' else None)
                self.assertFalse((root/'out').exists())

    def test_keys_other_reviewers_traversal_and_compressed_answers_are_rejected(self):
        extras = [('coordinator/answer_key.json', '{}'), ('../escape.txt', 'x'),
                  ('C:/escape.txt', 'x'), ('reviewer_2/annotations.csv', 'x'), ('INDEX.HTML', 'x')]
        for extra in extras:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root/'pilot.zip'
                reviewer_fixture(archive, extra=extra)
                with self.assertRaises(ValueError):
                    prepare_reviewer_workspace(archive, root/'out', 'pilot', 'fixture-reviewer')
                self.assertFalse((root/'out').exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root/'pilot.zip'
            reviewer_fixture(archive, evidence=dict(case_id='fixture-0', nested=dict(machine_label='dissolve')))
            with self.assertRaises(ValueError):
                prepare_reviewer_workspace(archive, root/'out', 'pilot', 'fixture-reviewer')

    def test_missing_case_evidence_does_not_pass_technical_intake(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root/'pilot.zip'
            reviewer_fixture(archive, evidence=dict(case_id='fixture-0', source_size=2))
            with self.assertRaisesRegex(ValueError, 'no machine-readable'):
                prepare_reviewer_workspace(archive, root/'out', 'pilot', 'fixture-reviewer')
            self.assertFalse((root/'out').exists())
