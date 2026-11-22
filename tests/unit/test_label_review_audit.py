import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.reporting.label_review_audit import audit_label_review_packet


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LabelReviewAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.packet = self.root / "packet"
        (self.packet / "reviewer").mkdir(parents=True)
        (self.packet / "coordinator").mkdir()
        token = "a" * 20
        cases = [dict(case_id="case-0001", feature_month="2015-01", label_month="2015-02",
                      focal_source="source-0", current_groups={"source-0": [token]},
                      next_overlapping_groups={"target-0": [token]},
                      evidence_scope="Observed reply-network memberships only.")]
        (self.packet / "reviewer/cases.json").write_text(json.dumps(cases), encoding="utf-8")
        answers = [dict(case_id="case-0001", label="grow", reason="fixture")]
        (self.packet / "coordinator/answer_key.json").write_text(json.dumps(answers), encoding="utf-8")
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

    def test_audits_safe_packet_without_writing_labels(self):
        result = audit_label_review_packet(self.packet, self.root / "audit")
        self.assertEqual(result["status"], "blinded_packet_verified")
        self.assertEqual(result["cases"], 1)
        evidence = (self.root / "audit/case-evidence-check.csv").read_text(encoding="utf-8")
        self.assertNotIn("grow", evidence)
        self.assertNotIn("fixture", evidence)

    def test_rejects_leaked_case_field(self):
        path = self.packet / "reviewer/cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        cases[0]["label"] = "grow"
        path.write_text(json.dumps(cases), encoding="utf-8")
        manifest_path = self.packet / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifact_hashes"]["reviewer/cases.json"] = digest(path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "leaked"):
            audit_label_review_packet(self.packet, self.root / "audit")


if __name__ == "__main__":
    unittest.main()
