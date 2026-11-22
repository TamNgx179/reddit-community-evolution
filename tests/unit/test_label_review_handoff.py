import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.reporting.label_review_handoff import package_label_review_handoff


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LabelReviewHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.packet = self.root / "packet"
        (self.packet / "reviewer").mkdir(parents=True)
        (self.packet / "coordinator").mkdir()
        token = "a" * 20
        cases = [dict(case_id="case-0001", focal_source="source-0", current_groups={"source-0": [token]},
                      next_overlapping_groups={}, feature_month="2015-01", label_month="2015-02",
                      evidence_scope="Observed reply-network memberships only.")]
        (self.packet / "reviewer/cases.json").write_text(json.dumps(cases), encoding="utf-8")
        (self.packet / "coordinator/answer_key.json").write_text(json.dumps([
            dict(case_id="case-0001", label="grow", reason="fixture")]), encoding="utf-8")
        with (self.packet / "reviewer/annotations.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("case_id", "reviewer", "human_label", "confidence", "rationale"))
            writer.writeheader()
            for reviewer in ("reviewer_a", "reviewer_b"):
                writer.writerow(dict(case_id="case-0001", reviewer=reviewer, human_label="", confidence="", rationale=""))
        hashes = {relative: digest(self.packet / relative) for relative in (
            "reviewer/cases.json", "reviewer/annotations.csv", "coordinator/answer_key.json")}
        (self.packet / "manifest.json").write_text(json.dumps(dict(
            status="prepared_pending_human_annotation", artifact_hashes=hashes)), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_reviewer_handoff_excludes_key_and_other_form(self):
        result = package_label_review_handoff(self.packet, self.root / "reviewer-a", "reviewer_a")
        self.assertEqual(result["status"], "reviewer_handoff_prepared")
        self.assertFalse((self.root / "reviewer-a/coordinator").exists())
        self.assertFalse((self.root / "reviewer-a/reviewer/reviewer_b.csv").exists())
        with (self.root / "reviewer-a/reviewer/reviewer_a.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["reviewer"] for row in rows], ["reviewer_a"])
        self.assertTrue((self.root / "reviewer-a/reviewer_a_handoff.zip").is_file())

    def test_coordinator_handoff_excludes_reviewer_evidence(self):
        result = package_label_review_handoff(self.packet, self.root / "coordinator", "coordinator")
        self.assertEqual(result["status"], "coordinator_handoff_prepared")
        self.assertTrue((self.root / "coordinator/coordinator/answer_key.json").is_file())
        self.assertFalse((self.root / "coordinator/reviewer").exists())
        self.assertTrue((self.root / "coordinator/coordinator_handoff.zip").is_file())

    def test_rejects_packet_with_changed_artifact(self):
        cases_path = self.packet / "reviewer/cases.json"
        cases_path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact hash differs"):
            package_label_review_handoff(self.packet, self.root / "reviewer-a", "reviewer_a")


if __name__ == "__main__":
    unittest.main()
