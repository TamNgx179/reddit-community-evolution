"""Exercise the exporter CLI and independent stdlib consumer in fresh processes."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from reddit_sna.benchmarks.fixtures import export_truth_fixtures
from reddit_sna.benchmarks.io import export_truth_fixture
from reddit_sna.config import load_config
from tests.support import ProjectCase

READER = Path(__file__).resolve().parents[2] / "scripts/read_truth_fixture.py"


class TruthFixtureRunTests(ProjectCase):
    def fixture_config(self):
        path = self.config("detection-tracking")
        self.change(path, "seed = 42", "seed = 11")
        return path

    def read(self, dataset):
        return subprocess.run(
            [sys.executable, "-I", str(READER), str(dataset)], cwd=self.root,
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )

    def test_cli_exports_both_datasets_and_isolated_reader_verifies_every_file(self):
        config = self.fixture_config()
        command = [sys.executable, "-m", "reddit_sna.benchmarks.fixtures", "--config", str(config),
                   "--run-id", "fixture-cli", "--start-month", "2020-12"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(json.loads(result.stdout)["run_directory"])
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["scope"], "truth-fixtures")
        self.assertEqual(manifest["completed_stages"], ["truth"])
        self.assertEqual(manifest["config"]["seed"], 11)
        self.assertEqual(manifest["datasets"], ["dev-stable-easy-g11", "dev-grow-easy-g11"])
        self.assertEqual(len(manifest["files"]), 12)
        for name, info in manifest["files"].items():
            self.assertEqual(sha256((run / name).read_bytes()).hexdigest(), info["sha256"])
        for dataset_id, count in (("dev-stable-easy-g11", 48), ("dev-grow-easy-g11", 54)):
            read = self.read(run / "datasets" / dataset_id)
            self.assertEqual(read.returncode, 0, read.stderr)
            summary = json.loads(read.stdout)
            self.assertIs(summary["verified"], True)
            self.assertEqual(summary["counts"]["memberships"], count)
            self.assertEqual(set(summary["communities"]), {"2020-12", "2021-01"})
        before = {path.relative_to(run).as_posix(): path.read_bytes() for path in run.rglob("*") if path.is_file()}
        repeated = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already exists", repeated.stderr)
        self.assertEqual(before, {path.relative_to(run).as_posix(): path.read_bytes()
                                  for path in run.rglob("*") if path.is_file()})
        self.assertEqual(self.marker.read_text(encoding="utf-8"), "synthetic input; preserve me")

    def test_failed_run_records_failure_and_preserves_finished_dataset(self):
        config = load_config(self.fixture_config())

        def fail_grow(destination, **kwargs):
            if kwargs["scenario"] == "grow":
                raise OSError("simulated grow export failure")
            return export_truth_fixture(destination, **kwargs)

        with patch("reddit_sna.benchmarks.fixtures.export_truth_fixture", side_effect=fail_grow):
            with self.assertRaisesRegex(OSError, "simulated"):
                export_truth_fixtures(config)
        manifest = json.loads((config.run_directory / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertIn("simulated", manifest["error"])
        stable = config.run_directory / "datasets/dev-stable-easy-g11"
        self.assertEqual(self.read(stable).returncode, 0)
        self.assertEqual(manifest["datasets"], ["dev-stable-easy-g11"])

    def test_unsafe_destination_namespace_or_month_is_rejected_before_writes(self):
        config = load_config(self.fixture_config())
        for invalid in (
            load_config(self.config("prediction")),
            replace(config, output_root=self.root / "data"),
            replace(config, seed=True),
        ):
            with self.subTest(config=invalid), self.assertRaises(ValueError):
                export_truth_fixtures(invalid)
        with self.assertRaises(ValueError):
            export_truth_fixtures(config, start_month="2020-13")
        self.assertFalse((self.root / "artifacts").exists())
        self.assertEqual(self.marker.read_text(encoding="utf-8"), "synthetic input; preserve me")

    def test_independent_reader_rejects_hash_and_semantic_corruption(self):
        config = load_config(self.fixture_config())
        run = export_truth_fixtures(config)
        source = run / "datasets/dev-grow-easy-g11"
        original_meta = (source / "metadata.json").read_bytes()
        cases = (
            ("truth/events.csv", lambda text: text.replace(",grow\n", ",stable\n"), False, "SHA-256 mismatch"),
            ("truth/events.csv", lambda text: text.replace(",grow\n", ",stable\n"), True, "events differ"),
            ("truth/links.csv", lambda text: text.replace(",2020-02,C\n", ",2020-02,K\n"), True, "links differ"),
            ("truth/membership.csv", lambda text: text + text.splitlines()[1] + "\n", True, "duplicate membership"),
        )
        for name, mutate, rehash, expected_error in cases:
            path = source / name
            original = path.read_bytes()
            with self.subTest(name=name, rehash=rehash):
                path.write_text(mutate(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
                if rehash:
                    meta = json.loads(original_meta)
                    meta["files"][name]["sha256"] = sha256(path.read_bytes()).hexdigest()
                    (source / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
                corrupted = path.read_bytes()
                read = self.read(source)
                self.assertEqual(read.returncode, 2, read.stdout)
                self.assertIn(expected_error, read.stderr)
                self.assertEqual(path.read_bytes(), corrupted)
            path.write_bytes(original)
            (source / "metadata.json").write_bytes(original_meta)
