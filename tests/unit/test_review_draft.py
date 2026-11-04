import csv
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.reporting.review_draft import create_ai_assisted_draft


class ReviewDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.blank = self.root / 'blank.csv'
        self.automated = self.root / 'automated.csv'
        with self.blank.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=('case_id', 'label', 'confidence', 'rationale'))
            writer.writeheader()
            writer.writerows([
                {'case_id': 'case-a', 'label': '', 'confidence': '', 'rationale': ''},
                {'case_id': 'case-b', 'label': '', 'confidence': '', 'rationale': ''},
            ])
        with self.automated.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=(
                'case_id', 'label', 'confidence', 'rationale', 'reviewer_type'))
            writer.writeheader()
            writer.writerows([
                {'case_id': 'case-a', 'label': 'grow', 'confidence': 'high', 'rationale': 'Evidence A', 'reviewer_type': 'automated'},
                {'case_id': 'case-b', 'label': 'unresolved', 'confidence': 'medium', 'rationale': 'Evidence B', 'reviewer_type': 'automated'},
            ])

    def tearDown(self):
        self.temp.cleanup()

    def test_creates_disclosed_unsubmitted_draft(self):
        result = create_ai_assisted_draft(self.blank, self.automated, self.root / 'draft', 'phuc')
        self.assertEqual(result['status'], 'unsubmitted_ai_assisted_draft')
        self.assertEqual(result['human_judgments_claimed'], 0)
        with (self.root / 'draft/reviewer_1.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row['label'] for row in rows], ['grow', 'unresolved'])
        metadata = json.loads((self.root / 'draft/submission-metadata.json').read_text(encoding='utf-8'))
        self.assertTrue(metadata['ai_assistance_seen'])
        self.assertIsNone(metadata['actual_submitted_at_utc'])

    def test_rejects_case_mismatch_or_overwrite(self):
        with self.automated.open('a', encoding='utf-8', newline='') as stream:
            csv.DictWriter(stream, fieldnames=(
                'case_id', 'label', 'confidence', 'rationale', 'reviewer_type')).writerow(
                    {'case_id': 'case-c', 'label': 'stable', 'confidence': 'high', 'rationale': 'Evidence C', 'reviewer_type': 'automated'})
        with self.assertRaisesRegex(ValueError, 'different case sets'):
            create_ai_assisted_draft(self.blank, self.automated, self.root / 'draft', 'phuc')


if __name__ == '__main__':
    unittest.main()
