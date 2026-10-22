"""Freeze verified full development evidence; never execute a held-out fixture."""

from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.artifacts import capture_run_provenance, save_run_manifest, source_snapshot
from reddit_sna.benchmarks.freeze import create_benchmark_freeze, load_benchmark_freeze
from reddit_sna.config import ConfigError, load_config
from reddit_sna.contracts import PipelineName
from reddit_sna.pipelines.detection_tracking import run_synthetic_benchmark

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("igraph", "leidenalg", "sklearn")), "install [graph,evaluation] for freeze integration")
class BenchmarkFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="freeze-reference-")
        cls.addClassCleanup(temporary.cleanup)
        root = Path(temporary.name)
        cls.copy_configs(root)
        config = load_config(root / "configs/detection_development.toml", run_id="reference")
        cls.reference = run_synthetic_benchmark(config, protocol=root / "configs/benchmark_week1_protocol.json")

    @staticmethod
    def copy_configs(root):
        (root / "configs").mkdir(parents=True)
        for name in ("detection_development.toml", "benchmark_week1.json", "benchmark_week1_protocol.json"):
            shutil.copyfile(ROOT / "configs" / name, root / "configs" / name)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="freeze-case-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "project with spaces"
        self.copy_configs(self.root)
        self.config = load_config(self.root / "configs/detection_development.toml", run_id="freeze-001")
        self.protocol = self.root / "configs/benchmark_week1_protocol.json"
        self.dev = self.root / "artifacts/detection-tracking/development"
        shutil.copytree(self.reference, self.dev)

    @staticmethod
    def tree(path):
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}

    def create(self):
        return create_benchmark_freeze(self.config, development_run=self.dev, protocol=self.protocol)

    def test_complete_full_development_freezes_without_algorithms_and_relocates_read_only(self):
        before = self.tree(self.dev)
        with patch("reddit_sna.pipelines.detection_tracking.export_graph_dataset") as generator, patch("reddit_sna.pipelines.detection_tracking.export_synthetic_detection") as detector:
            output = self.create()
            generator.assert_not_called()
            detector.assert_not_called()
        result = load_benchmark_freeze(output)
        manifest = result.manifest
        self.assertTrue(manifest["freeze_record_created"])
        self.assertFalse(manifest["evaluation_executed"])
        self.assertEqual(manifest["changes_from_development"], [])
        self.assertEqual(manifest["development"]["counts"], {"datasets": 18, "snapshots": 36, "snapshot_detector_runs": 108})
        self.assertEqual(manifest["development"]["manifest_sha256"], sha256(before["manifest.json"]).hexdigest())
        self.assertEqual(manifest["source"]["files"], source_snapshot()[2])
        self.assertTrue({r["dataset_id"] for r in manifest["schedules"]["development"]}.isdisjoint(r["dataset_id"] for r in manifest["schedules"]["evaluation"]))
        self.assertEqual(self.tree(self.dev), before)
        saved = self.tree(output)
        relocated = self.root / "relocated bundle"
        shutil.copytree(output, relocated)
        self.assertEqual(load_benchmark_freeze(relocated).manifest_sha256, result.manifest_sha256)
        self.assertEqual(self.tree(output), saved)

    def test_wrong_namespace_subset_failed_or_pending_development_rejects_before_output(self):
        bad = replace(self.config, pipeline=PipelineName.PREDICTION)
        with self.assertRaisesRegex(ConfigError, "freeze requires"):
            create_benchmark_freeze(bad, development_run=self.dev, protocol=self.protocol)
        original = (self.dev / "manifest.json").read_bytes()
        for mutation in (lambda m: m.update(status="failed"),
                         lambda m: m["selection"].update(mode="development-subset"),
                         lambda m: m["dataset_records"][m["selection"]["dataset_ids"][0]]["detection"].update(status="pending")):
            manifest = json.loads(original)
            mutation(manifest)
            (self.dev / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.subTest(manifest=manifest["status"]), self.assertRaises(ConfigError):
                self.create()
            self.assertFalse(self.config.run_directory.exists())
        (self.dev / "manifest.json").write_bytes(original)
        (self.dev / "manifest.pending.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ConfigError, "pending marker"):
            self.create()

    def test_config_output_source_and_environment_drift_reject_before_freeze(self):
        original = self.config.source.read_bytes()
        self.config.source.write_bytes(original + b"\n")
        with self.assertRaisesRegex(ConfigError, "configuration differs: run_config"):
            self.create()
        self.config.source.write_bytes(original)
        target = self.dev / "evaluation/detection_metrics.csv"
        original = target.read_bytes()
        target.write_bytes(original + b"\n")
        with self.assertRaisesRegex(ConfigError, "output inventory"):
            self.create()
        target.write_bytes(original)
        for side in ("source", "environment"):
            source, environment, blobs = capture_run_provenance()
            if side == "source":
                source["files"]["reddit_sna/benchmarks/freeze.py"] = "0" * 64
            else:
                environment["packages"]["numpy"] = "different-version"
            with self.subTest(side=side), patch("reddit_sna.benchmarks.freeze.capture_run_provenance", return_value=(source, environment, blobs)), self.assertRaisesRegex(ConfigError, "runtime"):
                self.create()
            self.assertFalse(self.config.run_directory.exists())

    def test_existing_freeze_is_immutable_and_loader_rejects_changed_bytes_or_runtime(self):
        output = self.create()
        before = self.tree(output)
        with self.assertRaisesRegex(ConfigError, "run already exists"):
            self.create()
        self.assertEqual(self.tree(output), before)
        target = output / "config/protocol/benchmark_week1.json"
        original = target.read_bytes()
        target.write_bytes(original + b" ")
        with self.assertRaisesRegex(ConfigError, "output inventory"):
            load_benchmark_freeze(output)
        target.write_bytes(original)
        source, environment, blobs = capture_run_provenance()
        source["files"]["reddit_sna/benchmarks/freeze.py"] = "0" * 64
        with patch("reddit_sna.benchmarks.freeze.capture_run_provenance", return_value=(source, environment, blobs)), self.assertRaisesRegex(ConfigError, "runtime source"):
            load_benchmark_freeze(output)
        (output / "failure.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ConfigError, "failure/pending marker"):
            load_benchmark_freeze(output)

    def test_late_publication_failure_keeps_failed_bundle_and_original_development(self):
        before = self.tree(self.dev)
        def failed_complete(run, manifest):
            if manifest["status"] == "complete":
                raise OSError("freeze publication failed")
            save_run_manifest(run, manifest)
        with patch("reddit_sna.benchmarks.freeze.save_run_manifest", side_effect=failed_complete), self.assertRaisesRegex(OSError, "freeze publication failed"):
            self.create()
        failed = json.loads((self.config.run_directory / "manifest.json").read_bytes())
        self.assertEqual(failed["status"], "failed")
        self.assertFalse(failed["freeze_record_created"])
        self.assertIsNone(failed["frozen_at"])
        self.assertTrue(failed["files"])
        self.assertEqual(self.tree(self.dev), before)
        with self.assertRaisesRegex(ConfigError, "complete supported manifest"):
            load_benchmark_freeze(self.config.run_directory)

    def test_existing_heldout_identity_metadata_blocks_a_pre_evaluation_claim(self):
        # Identity-only guard fixture; no held-out graph or labels are generated/read.
        folder = self.root / "artifacts/detection-tracking/identity-fixture/inputs/source/eval-example"
        folder.mkdir(parents=True)
        (folder / "metadata.json").write_text(json.dumps({"artifact_type": "synthetic-graph-truth", "split": "evaluation"}), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "held-out output metadata already exists"):
            self.create()
        self.assertFalse(self.config.run_directory.exists())

    def test_cli_create_verify_and_retry_from_outside_repository(self):
        create = [sys.executable, "-m", "reddit_sna.benchmarks.freeze", "create", "--config", str(self.config.source),
                  "--protocol", str(self.protocol), "--development-run", str(self.dev), "--run-id", self.config.run_id]
        result = subprocess.run(create, cwd=self.root, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["evaluation_executed"])
        before = self.tree(self.config.run_directory)
        verified = subprocess.run([sys.executable, "-m", "reddit_sna.benchmarks.freeze", "verify", data["directory"]], cwd=self.root,
                                  capture_output=True, text=True, timeout=90)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["manifest_sha256"], data["manifest_sha256"])
        repeated = subprocess.run(create, cwd=self.root, capture_output=True, text=True, timeout=90)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(repeated.stdout, "")
        self.assertEqual(self.tree(self.config.run_directory), before)
