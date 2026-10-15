"""Independent consumer contract tests with temporary synthetic public files."""

import importlib.util
import json
from pathlib import Path
import unittest

from reddit_sna.config import load_config
from reddit_sna.data.archive import digest_file
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.reporting.handoff import inspect_handoff
from tests.corpus_support import CorpusCase


@unittest.skipUnless(importlib.util.find_spec("leidenalg"), "install [graph]")
class HandoffTests(CorpusCase):
    def setUp(self):
        super().setUp()
        self.raw()
        self.run = run_preparation(load_config(self.config("core")), corpora=("moderatepolitics",))

    def inspect(self):
        return inspect_handoff(self.run, self.run, self.root / "artifacts")

    def reseal(self, relative, text):
        """Re-seal bytes to test semantics beyond simple corruption detection."""
        (self.run / relative).write_text(text, encoding="utf-8")
        manifest = json.loads((self.run / "manifest.json").read_text())
        manifest["artifact_hashes"][str(Path(relative))] = digest_file(self.run / relative)
        (self.run / "manifest.json").write_text(json.dumps(manifest))

    def test_accepts_canonical_memberships_and_empty_months_without_partner_claim(self):
        result = self.inspect()
        self.assertEqual(result["status"], "accepted_by_automated_consumer")
        self.assertEqual(result["partner_acceptance"], "not_verified")
        self.assertEqual(result["transition_opportunities"], 2)
        self.assertEqual([m["assigned_users"] for m in result["months"]], [2, 0, 0])

    def test_hash_corruption_rejected(self):
        with (self.run / "detection.json").open("a") as handle:
            handle.write(" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.inspect()

    def test_resealed_duplicate_membership_rejected(self):
        relative = "memberships/2015-01/membership-seed0.csv"
        text = (self.run / relative).read_text()
        self.reseal(relative, text + text.splitlines()[1] + "\n")
        with self.assertRaisesRegex(ValueError, "duplicate membership"):
            self.inspect()

    def test_resealed_missing_endpoint_rejected(self):
        relative = "memberships/2015-01/membership-seed0.csv"
        text = (self.run / relative).read_text().splitlines()
        self.reseal(relative, "\n".join(text[:2])+"\n")
        with self.assertRaisesRegex(ValueError, "endpoint mismatch"):
            self.inspect()

    def test_resealed_wrong_reference_rejected(self):
        relative = "memberships/2015-01/membership-seed0.csv"
        text = (self.run / relative).read_text()
        reference = text.splitlines()[1].split(",")[0]
        self.reseal(relative, text.replace(reference, "wrong-reference"))
        with self.assertRaisesRegex(ValueError, "reference/key"):
            self.inspect()

    def test_resealed_schema_change_rejected(self):
        relative = "memberships/2015-01/membership-seed0.csv"
        self.reseal(relative, (self.run / relative).read_text().replace("community_id", "cluster"))
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            self.inspect()

    def test_unhashed_public_summary_rejected(self):
        manifest = json.loads((self.run / "manifest.json").read_text())
        del manifest["artifact_hashes"]["detection.json"]
        (self.run / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "summary missing"):
            self.inspect()

    def test_resealed_nonfinite_edge_rejected(self):
        relative = "snapshots/2015-01/R.csv"
        lines = (self.run / relative).read_text().splitlines()
        fields = lines[1].split(","); fields[-1] = "nan"
        self.reseal(relative, lines[0]+"\n"+",".join(fields)+"\n")
        with self.assertRaisesRegex(ValueError, "invalid R edge"):
            self.inspect()

    def test_resealed_period_mismatch_rejected(self):
        data = json.loads((self.run / "detection.json").read_text())
        data["end_month_exclusive"] = "2015-05"
        self.reseal("detection.json", json.dumps(data))
        with self.assertRaisesRegex(ValueError, "period/reference"):
            self.inspect()

    def test_sources_outside_artifact_boundary_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside artifacts"):
            inspect_handoff(self.run, self.run, self.root / "other")

    def test_separate_detection_source_link_and_replacement_rejection(self):
        config = load_config(self.config("core"),run_id="derived-detection")
        derived = run_preparation(config,stage="detect",source_run=self.run)
        accepted = inspect_handoff(self.run,derived,self.root/"artifacts")
        self.assertEqual(accepted["status"],"accepted_by_automated_consumer")
        manifest = json.loads((derived/"manifest.json").read_text())
        manifest["source_manifest_sha256"] = "0"*64
        (derived/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"source linkage"):
            inspect_handoff(self.run,derived,self.root/"artifacts")
