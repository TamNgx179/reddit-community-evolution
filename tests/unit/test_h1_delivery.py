"""Reject corrupted and unsafe saved payloads before exporting delivery evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.data.archive import digest_file
from scripts.verify_h1_delivery import verify_inventory


class DeliveryInventoryTests(unittest.TestCase):
    def test_rejects_changed_payload_and_incomplete_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "predictions.csv"
            payload.write_text("original", encoding="utf-8")
            manifest = dict(status="complete", artifact_hashes={payload.name: digest_file(payload)})
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(verify_inventory(root), manifest)
            payload.write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_inventory(root)
            manifest["status"] = "started"
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_inventory(root)

    def test_rejects_inventory_path_outside_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "run"
            output.mkdir()
            payload = root / "outside.csv"
            payload.write_text("data", encoding="utf-8")
            (output / "manifest.json").write_text(json.dumps(dict(status="complete",
                artifact_hashes={"../outside.csv": digest_file(payload)})), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_inventory(output)


if __name__ == "__main__":
    unittest.main()
