"""Real-file acceptance tests, including semantic failures after valid rehashing."""

import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.artifact_acceptance import (
    inspect_contract, package_delivery, relative_path, run_acceptance, verify_bundle,
    write_json,
)


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "artifacts/frozen"
        self.data.mkdir(parents=True)
        self.contract_path = self.root / "configs/contract.json"
        self.contract_path.parent.mkdir()
        self.features = [dict(reference_id="r", feature_month=month, community_id=cid,
                              available_through_month=month, size="2", history_missing="1")
                         for month, cid in (("2020-01", "a"), ("2020-01", "b"), ("2020-02", "a"))]
        self.labels = [dict(reference_id="r", feature_month="2020-01", community_id=cid,
                            label_month="2020-02", label_reference_id="l", eligible=eligible,
                            label=label, reason=reason)
                       for cid, eligible, label, reason in (("a", "1", "stable", "accepted"),
                                                            ("b", "0", "", "ambiguous"))]
        self.samples = [self.labels[0].copy()]
        self.predictions = [dict(**{k: self.samples[0][k] for k in
                            ("reference_id", "feature_month", "community_id", "label_month", "label_reference_id")},
                                 model="HGB", seed=str(seed), y_true="stable", y_pred=pred)
                            for seed, pred in ((42, "stable"), (43, "grow"))]
        self.protocol = dict(seeds=[42, 43], test_start="2020-02")
        self.contract = dict(schema_version=1, h1_required_paths=["artifacts/missing-h1"], cohorts=[dict(
            name="fixture", reference_id="r", label_reference_id="l", terminal_month="2020-02",
            evaluation_start="2020-02", boundary_field="test_start", seeds=[42, 43],
            feature_columns=list(self.features[0]), expected_status_counts=dict(resolved=1, unresolved=1, censored=1),
            windows=dict(final=["2020-02"]), expected_window_n=dict(final=1),
            predictions=[dict(file="predictions", models=["HGB"], default_window="final")])])
        self.seal()

    def seal(self):
        """Rehash mutated fixture data so negative controls test semantics, not just hashes."""
        for name, rows in (("features", self.features), ("labels", self.labels),
                           ("samples", self.samples), ("predictions", self.predictions)):
            with (self.data / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        write_json(self.data / "protocol.json", self.protocol)
        inventory = {p.name: digest_file(p) for p in self.data.iterdir() if p.name != "manifest.json"}
        # Unselected historical payload is deliberately unavailable locally.
        inventory["historical\\omitted.json"] = "0" * 64
        write_json(self.data / "manifest.json", dict(status="complete", artifact_hashes=inventory))
        cohort = self.contract["cohorts"][0]
        cohort["files"] = {name: dict(path=f"artifacts/frozen/{name}.{extension}",
                                     sha256=digest_file(self.data / f"{name}.{extension}"), manifest="source")
                           for name, extension in (("features", "csv"), ("labels", "csv"), ("samples", "csv"),
                                                    ("predictions", "csv"), ("protocol", "json"))}
        cohort["manifests"] = dict(source=dict(path="artifacts\\frozen\\manifest.json",
                                               sha256=digest_file(self.data / "manifest.json")))
        write_json(self.contract_path, self.contract)

    def accept(self, name="inputs", **kwargs):
        return run_acceptance(self.root, self.contract_path, self.root / "artifacts" / name, **kwargs)

    def test_valid_receipt_legacy_terminal_and_replay(self):
        first = self.accept()
        self.assertEqual(first["cohorts"][0]["status_counts"], dict(resolved=1, unresolved=1, censored=1))
        self.assertEqual(first["cohorts"][0]["community_month_coverage"], 0.5)
        self.assertEqual(first["h1_dependency"]["missing_paths"], ["artifacts/missing-h1"])
        self.assertEqual(first["h1_dependency"]["status"], "pending_missing_inputs")
        self.assertIn("Selected", first["cohorts"][0]["verification_scope"])
        self.accept("replay", accepted_input=self.root / "artifacts/inputs")
        with (self.root / "artifacts/replay/replayed-metrics.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertAlmostEqual(float(rows[0]["macro_f1_six"]), 1 / 6)
        self.assertEqual(float(rows[1]["macro_f1_six"]), 0)
        self.assertEqual(rows[0]["n"], "1")
        for name, expected in first["input_sha256"].items():
            self.assertEqual(digest_file(relative_path(self.root, name)), expected)

    def test_changed_input_records_failure_and_preserves_prior_output(self):
        self.accept()
        path = self.data / "features.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Changed selected"):
            self.accept("bad")
        self.assertEqual(json.loads((self.root / "artifacts/bad/failure.json").read_text())["status"], "failed")
        with self.assertRaises(FileExistsError):
            self.accept()

    def test_duplicate_prediction(self):
        self.predictions.append(self.predictions[0].copy())
        self.seal()
        with self.assertRaisesRegex(ValueError, "Duplicate keyed"):
            self.accept()

    def test_wrong_truth(self):
        self.predictions[0]["y_true"] = "grow"
        self.seal()
        with self.assertRaisesRegex(ValueError, "truth/window"):
            self.accept()

    def test_missing_seed(self):
        self.predictions.pop()
        self.seal()
        with self.assertRaisesRegex(ValueError, "Incomplete model"):
            self.accept()

    def test_mixed_reference(self):
        self.features[0]["reference_id"] = "other"
        self.seal()
        with self.assertRaisesRegex(ValueError, "Feature references"):
            self.accept()

    def test_future_feature_cutoff(self):
        self.features[0]["available_through_month"] = "2020-02"
        self.seal()
        with self.assertRaisesRegex(ValueError, "availability"):
            self.accept()

    def test_schema_order(self):
        self.features = [dict(reversed(list(r.items()))) for r in self.features]
        self.seal()
        with self.assertRaisesRegex(ValueError, "schema/order"):
            self.accept()

    def test_nonfinite_cache(self):
        self.features[0]["size"] = "nan"
        self.seal()
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            self.accept()

    def test_censored_scoring_rejected(self):
        self.predictions[0]["feature_month"] = "2020-02"
        self.predictions[0]["label_month"] = "2020-03"
        self.seal()
        with self.assertRaisesRegex(ValueError, "truth/window"):
            self.accept()

    def test_missing_window_without_explicit_declaration(self):
        del self.contract["cohorts"][0]["predictions"][0]["default_window"]
        self.seal()
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.accept()

    def test_window_cutoff(self):
        self.protocol["test_start"] = "2020-03"
        self.contract["cohorts"][0]["evaluation_start"] = "2020-03"
        self.seal()
        with self.assertRaisesRegex(ValueError, "overlaps earlier"):
            self.accept()

    def test_paths_and_output_overlap(self):
        for name in ("../secret", "C:\\private", "/tmp/private", ".", "a/../../b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                relative_path(self.root, name)
        with self.assertRaisesRegex(ValueError, "overlaps frozen"):
            self.accept("frozen/output")

    def test_escaping_symlink(self):
        # Directory junction creation on Windows does not require symlink privilege.
        target = self.root.parent
        link = self.root / "escape"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if __import__("os").name != "nt":
                raise
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        self.addCleanup(lambda: link.unlink() if link.is_symlink() else link.rmdir())
        with self.assertRaisesRegex(ValueError, "escapes root"):
            relative_path(self.root, "escape/external.csv")

    def test_prior_receipt_corruption(self):
        self.accept()
        path = self.root / "artifacts/inputs/acceptance.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "receipt payload changed"):
            self.accept("replay", accepted_input=path.parent)

    def test_missing_manifest_and_missing_nonterminal_labels(self):
        self.data.joinpath("manifest.json").unlink()
        with self.assertRaises(FileNotFoundError):
            inspect_contract(self.root, self.contract_path)
        self.labels.pop()
        self.seal()
        with self.assertRaisesRegex(ValueError, "Missing nonterminal"):
            self.accept()

    def test_bundle_exact_inventory_tamper_and_reuse(self):
        actual = Path(__file__).resolve().parents[2]
        # Populate real product sources. The bundle's allowlist must exclude extras.
        shutil.copytree(actual / "src", self.root / "src")
        for name in ("pyproject.toml", "README.md", "docs/WEEK4_HANDOFF.md",
                     "scripts/verify_week4_inputs.py", "scripts/run_week4_acceptance.py",
                     "scripts/package_week4_handoff.py", "tests/unit/test_artifact_acceptance.py"):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(actual / name, destination)
        (self.data / "answer-key.json").write_text("private")
        self.accept()
        self.accept("replay", accepted_input=self.root / "artifacts/inputs")
        target = self.root / "dist/delivery.zip"
        package_delivery(self.root, self.root / "artifacts/replay", target)
        inventory = verify_bundle(target)
        self.assertNotIn("artifacts/frozen/answer-key.json", inventory["sha256"])
        self.assertIn("src/reddit_sna/evaluation/artifact_acceptance.py", inventory["sha256"])
        self.assertNotIn(".harness", " ".join(inventory["sha256"]))
        with self.assertRaises(FileExistsError):
            package_delivery(self.root, self.root / "artifacts/replay", target)
        altered = self.root / "dist/changed.zip"
        with zipfile.ZipFile(target) as source, zipfile.ZipFile(altered, "w") as dest:
            for name in source.namelist():
                dest.writestr(name, b"changed" if name == "README.md" else source.read(name))
        with self.assertRaisesRegex(ValueError, "payload changed"):
            verify_bundle(altered)


if __name__ == "__main__":
    unittest.main()
