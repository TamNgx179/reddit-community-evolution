"""Verify cross-pipeline compatibility and a fresh, non-historical group demo."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.config import load_config
from reddit_sna.contracts import Event
from reddit_sna.pipelines.synthetic_week1 import run_demo
from reddit_sna.reporting.tracking_outputs import INPUT_PINS, run_split, run_current_split
from reddit_sna.reporting.tracking_demo import read_tracking_run
from reddit_sna.tracking.jaccard import transitions, track


PROJECT = Path(__file__).resolve().parents[2]


def prepare_project(root):
    """Supply only the declared versioned inputs; never copy a runtime dataset."""
    for relative in ("configs/detection_development.toml", "configs/benchmark_week1.json",
                     "configs/benchmark_week1_protocol.json", "scripts/run_frozen_evaluation.py",
                     "notebooks/detection_tracking/01_synthetic_demo.ipynb"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT / relative, target)
    return root / "configs/detection_development.toml"


class SyntheticGroupDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="group-delivery-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.config = prepare_project(cls.root)
        cls.output = run_demo(cls.config, "fresh-pair")
        cls.manifest = json.loads((cls.output / "manifest.json").read_text(encoding="utf-8"))

    def test_full_generation_to_tracking_and_plots_without_legacy_bundle(self):
        self.assertEqual(self.manifest["status"], "complete")
        self.assertEqual(self.manifest["figures"], 8)
        self.assertFalse((self.root / "artifacts/handoff/phuc-dang-week1-20261019-001").exists())
        rows = self.manifest["tracking_summary"]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["support"], 39)
            if row["route"] == "truth_tracking":
                self.assertEqual(row["pooled_macro_f1"], 1)
                self.assertEqual(row["correct"], 39)
        for directory, count in (("detection-report", 4), ("case-report", 2), ("tracking-report", 2)):
            figure_root = self.output / directory / "figures" if directory == "detection-report" else self.output / directory
            self.assertEqual(len(list(figure_root.glob("*.png"))), count)
            self.assertEqual(len(list(figure_root.glob("*.svg"))), count)

    def test_freeze_chronology_and_new_pins_are_explicit(self):
        stage = self.output / "workspace/artifacts/detection-tracking"
        frozen = json.loads((stage / "freeze/manifest.json").read_text(encoding="utf-8"))
        evaluation = json.loads((stage / "evaluation/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(evaluation["freeze_reference"]["manifest_sha256"],
                         sha256((stage / "freeze/manifest.json").read_bytes()).hexdigest())
        self.assertLessEqual(frozen["frozen_at"], evaluation["created_at"])
        self.assertIn("not a new unseen test", self.manifest["interpretation"])
        self.assertEqual(self.manifest["partner_acceptance"], "not_verified")
        self.assertEqual(self.manifest["historical_dang_freeze"], "not_verified")
        self.assertEqual(set(self.manifest["source_manifest_sha256"]), {"development", "evaluation"})
        self.assertNotEqual(self.manifest["source_manifest_sha256"], INPUT_PINS)

    def test_new_report_requires_its_own_explicit_input_pin(self):
        path = self.output / "tracking/development"
        with self.assertRaisesRegex(ValueError, "pin"):
            read_tracking_run(path, split="development")
        verified = read_tracking_run(path, split="development",
                                     expected_input_sha256=self.manifest["source_manifest_sha256"]["development"])
        self.assertEqual(len(verified["records"]), 78)
        with self.assertRaisesRegex(ValueError, "pin"):
            run_split(self.root / "missing", self.root / "artifacts", run_id="legacy-bad-pin",
                      split="development", source_run="not-the-original", input_manifest_sha256="0" * 64)

    def test_immutable_destination_and_source_pin_refusal(self):
        before = (self.output / "manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            run_demo(self.config, "fresh-pair")
        self.assertEqual((self.output / "manifest.json").read_bytes(), before)
        source = self.output / "workspace/artifacts/detection-tracking/development"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            run_current_split(source, self.root / "artifacts", run_id="corrupt-source",
                              split="development", source_manifest_sha256="0" * 64)
        self.assertFalse((self.root / "artifacts/corrupt-source").exists())

    def test_wrong_config_and_missing_backend_do_not_reserve_outputs(self):
        original = self.config.read_text(encoding="utf-8")
        alternate = self.config.with_name("wrong-seed.toml")
        alternate.write_text(original.replace("seed = 0", "seed = 42"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "seed 0"):
            run_demo(alternate, "wrong-seed")
        with patch("reddit_sna.detection.leiden.dependencies", side_effect=ValueError("missing graph extra")):
            with self.assertRaisesRegex(ValueError, "missing graph extra"):
                run_demo(self.config, "missing-backend")
        self.assertFalse((self.root / "artifacts/detection-tracking/missing-backend").exists())

    def test_failed_driver_leaves_a_failed_parent_not_false_completion(self):
        def fail(*args, **kwargs):
            raise OSError("simulated driver failure")
        with patch("reddit_sna.pipelines.synthetic_week1._evaluation_driver", return_value=fail):
            with self.assertRaisesRegex(OSError, "driver failure"):
                run_demo(self.config, "driver-failure")
        manifest = json.loads((self.root / "artifacts/detection-tracking/driver-failure/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["failure_type"], "OSError")


class GroupCompatibilityTests(unittest.TestCase):
    def test_tracker_policies_and_return_contracts_stay_distinct(self):
        source = {"a": {str(i) for i in range(20)}}
        target = {"b": {*source["a"], "new"}}
        links, labels = transitions(source, target)
        self.assertEqual(labels["a"], Event.GROW)
        self.assertIn("a", links)
        self.assertEqual(track(source, target)["events"][0]["event"], "stable")

    def test_source_does_not_depend_on_retired_report_or_document_folders(self):
        self.assertFalse((PROJECT / "document").exists())
        self.assertEqual([p.relative_to(PROJECT / "reports").as_posix()
                          for p in (PROJECT / "reports").rglob("*") if p.is_file()], ["WEEK1_REPORT.md"])
        for folder in ("src", "scripts", "configs"):
            for path in (PROJECT / folder).rglob("*"):
                if path.is_file() and path.suffix in {".py", ".json", ".toml"}:
                    self.assertNotIn('"document/', path.read_text(encoding="utf-8"), str(path))


class PredictionReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from reddit_sna.pipelines.prediction import run
        cls.temp = tempfile.TemporaryDirectory(prefix="prediction-report-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        (cls.root / "configs").mkdir()
        path = cls.root / "configs/prediction.toml"
        shutil.copy2(PROJECT / "configs/prediction.toml", path)
        cls.run_dir = run(load_config(path, run_id="verified-prediction"))

    def test_metric_reconstruction_and_real_heldout_figures(self):
        from matplotlib import pyplot as plt
        from reddit_sna.reporting.prediction import read_prediction, build_prediction_figures
        report = read_prediction(self.run_dir)
        self.assertEqual(set(report["metrics"]["model"]), {"B1_majority", "B1_persistence", "B4_logreg"})
        self.assertIn("macro_f1_six", report["metrics"])
        figures = build_prediction_figures(report)
        self.assertEqual(len(figures), 5)
        for figure in figures.values():
            self.assertTrue(figure.axes)
            plt.close(figure)

    def test_corrupt_metrics_and_resealed_incomplete_population_are_rejected(self):
        import pandas as pd
        from reddit_sna.reporting.prediction import read_prediction
        copied = self.root / "corrupt"
        shutil.copytree(self.run_dir, copied)
        (copied / "metrics.csv").write_text("corrupt", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash"):
            read_prediction(copied)
        manifest = json.loads((self.run_dir / "manifest.json").read_text(encoding="utf-8"))
        rows = pd.read_csv(self.run_dir / "predictions.csv").iloc[1:]
        rows.to_csv(copied / "predictions.csv", index=False)
        shutil.copy2(self.run_dir / "metrics.csv", copied / "metrics.csv")
        manifest["artifact_hashes"]["predictions.csv"] = sha256((copied / "predictions.csv").read_bytes()).hexdigest()
        (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "population"):
            read_prediction(copied)
        rows = pd.read_csv(self.run_dir / "predictions.csv").query("model != 'B4_logreg'")
        rows.to_csv(copied / "predictions.csv", index=False)
        manifest["artifact_hashes"]["predictions.csv"] = sha256((copied / "predictions.csv").read_bytes()).hexdigest()
        (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "baseline model"):
            read_prediction(copied)
