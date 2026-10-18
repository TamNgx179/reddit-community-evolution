"""Exercise delivery on synthetic archives and actual verified CSV artifacts."""

import builtins
import contextlib
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile

from reddit_sna.cli import main
from reddit_sna.config import load_config
from reddit_sna.data.archive import digest_file
from reddit_sna.pipelines.forecast import run_forecast
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.pipelines.week1 import run_demo
from reddit_sna.reporting.forecast import summarize, build_figures, export_report
from reddit_sna.reporting.forecast_handoff import read_handoff
from reddit_sna.reporting.label_review import prepare_review
from tests.corpus_support import CorpusCase, record


class WeekOneDeliveryTests(CorpusCase):
    def setUp(self):
        super().setUp()
        self.raw([record("p", "synthetic_A", day="2014-12-01"),
                  *[record(f"r{i}", "synthetic_B", parent="p", day=f"2015-{i:02d}-02") for i in range(1, 4)]])
        self.config_path = self.config("core")
        with contextlib.redirect_stdout(io.StringIO()):
            self.source = run_preparation(load_config(self.config_path), corpora=("moderatepolitics",))
        self.artifacts = self.root / "artifacts"
        self.forecast = self.artifacts / "core/forecast"
        run_forecast(self.source, self.source, self.artifacts, self.forecast, "2015-03", tracker="ged", history=True)

    def reseal(self, relative, value):
        """Bypass the byte check deliberately to exercise semantic checks."""
        path = self.forecast / relative
        path.write_text(json.dumps(value), encoding="utf-8")
        manifest_path = self.forecast / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifact_hashes"][relative] = digest_file(path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_offline_handoff_keeps_document_navigation_and_verified_artifacts(self):
        """Exercise the real packaging CLI and independently read its extracted delivery."""
        project = Path(__file__).resolve().parents[2]
        archive = self.root / "delivery.zip"
        command = [sys.executable, str(project / "scripts/package_forecast.py"),
                   "--run", str(self.forecast), "--output", str(archive)]
        packaged = subprocess.run(command, cwd=project, capture_output=True, text=True)
        self.assertEqual(packaged.returncode, 0, packaged.stderr)
        documents = ("README.md", "PHAN-CONG-SNA-8-TUAN.md", "docs/METHODS.md",
                     "docs/RUNBOOK.md", "docs/RESULTS.md", "docs/LABEL_REVIEW.md")
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual({name for name in bundle.namelist() if name.endswith(".md")}, set(documents))
            for relative in documents:
                self.assertEqual(bundle.read(relative), (project / relative).read_bytes())
            bundle.extractall(self.root / "extracted")
        extracted = read_handoff(self.root / "extracted")
        self.assertEqual(extracted["metrics"], read_handoff(self.forecast)["metrics"])
        before = archive.read_bytes()
        repeated = subprocess.run(command, cwd=project, capture_output=True, text=True)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(archive.read_bytes(), before)

    def test_report_retains_absent_classes_and_recomputes_month_scores(self):
        report = summarize(self.forecast)
        self.assertEqual(len(report["classes"]), 6)
        self.assertEqual(next(r for r in report["classes"] if r["event"] == "merge"), {"event": "merge", "train": 0, "test": 0})
        self.assertEqual(report["coverage"], dict(total_transitions=2, eligible=2, excluded=0, exclusion_fraction=0))
        self.assertEqual(report["monthly_scores"][0]["macro_f1"], 1/6)
        self.assertEqual(report["delivery"]["development_folds"], [])
        self.assertEqual(report["delivery"]["errors"], [])

    def test_figures_and_source_bound_export_are_real_and_immutable(self):
        from matplotlib import pyplot as plt
        figures = build_figures(summarize(self.forecast))
        self.assertEqual(len(figures), 6)
        for figure in figures.values():
            self.assertTrue(figure.axes)
            plt.close(figure)
        destination = self.artifacts / "core/report"
        export_report(self.forecast, destination, self.artifacts)
        manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(len(list(destination.glob("*.png"))), 6)
        self.assertEqual(len(list(destination.glob("*.svg"))), 6)
        for relative, expected in manifest["artifact_hashes"].items():
            self.assertEqual(digest_file(destination / relative), expected)
        with self.assertRaises(FileExistsError):
            export_report(self.forecast, destination, self.artifacts)
        with self.assertRaises(ValueError):
            export_report(self.forecast, self.root / "outside", self.artifacts)
        with self.assertRaisesRegex(ValueError, "immutable"):
            export_report(self.forecast, self.forecast / "nested-report", self.artifacts)
        self.assertFalse((self.forecast / "nested-report").exists())

    def test_missing_plot_dependency_has_actionable_guidance(self):
        original = builtins.__import__
        def missing(name, *args, **kwargs):
            if name.startswith("matplotlib"):
                raise ImportError("simulated missing optional plot dependency")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing):
            with self.assertRaisesRegex(RuntimeError, "pip install"):
                build_figures(summarize(self.forecast))

    def test_corrupt_hash_fails_before_export(self):
        with (self.forecast / "predictions.csv").open("a", encoding="utf-8") as stream:
            stream.write("corrupt")
        destination = self.artifacts / "core/bad-report"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            export_report(self.forecast, destination, self.artifacts)
        self.assertFalse(destination.exists())

    def test_resealed_quality_and_class_metrics_are_rejected(self):
        quality = json.loads((self.forecast / "quality.json").read_text(encoding="utf-8"))
        for change in ({"test_support": {"stable": 100}}, {"unresolved": 5}, {"monthly_support": {}}, {"dominant_test_fraction": 0.1}):
            with self.subTest(change=change):
                self.reseal("quality.json", {**quality, **change})
                with self.assertRaisesRegex(ValueError, "Quality"):
                    summarize(self.forecast)
        self.reseal("quality.json", quality)
        metrics = json.loads((self.forecast / "metrics.json").read_text(encoding="utf-8"))
        metrics["models"]["majority"]["per_class"]["stable"]["recall"] = 0.5
        self.reseal("metrics.json", metrics)
        with self.assertRaisesRegex(ValueError, "Per-class"):
            summarize(self.forecast)

    def test_resealed_error_examples_are_rejected(self):
        file = self.forecast / "errors.csv"
        file.write_text((self.forecast / "predictions.csv").read_text(encoding="utf-8"), encoding="utf-8")
        manifest_path = self.forecast / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifact_hashes"]["errors.csv"] = digest_file(file)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Error examples"):
            summarize(self.forecast)

    def test_resealed_fold_boundaries_and_empty_cohort_are_rejected(self):
        self.reseal("development_folds.json", [{"test_start_label_month": "2015-03"}])
        with self.assertRaisesRegex(ValueError, "fold boundaries"):
            summarize(self.forecast)
        self.reseal("development_folds.json", [])
        manifest_path = self.forecast / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["actual_months"] = []
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "month cohort"):
            summarize(self.forecast)

    def test_review_is_deterministic_blinded_and_never_fills_human_labels(self):
        paths = [self.artifacts / "core/review-a", self.artifacts / "core/review-b"]
        for destination in paths:
            prepare_review(self.forecast, self.source, self.source, destination, self.artifacts, per_stratum=50, seed=7)
        for relative in ("reviewer/cases.json", "reviewer/annotations.csv", "coordinator/answer_key.json"):
            self.assertEqual((paths[0] / relative).read_bytes(), (paths[1] / relative).read_bytes())
        manifest = json.loads((paths[0] / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["sampled_cases"], 2)  # Do not manufacture 50 cases.
        self.assertEqual(manifest["status"], "prepared_pending_human_annotation")
        evidence = json.loads((paths[0] / "reviewer/cases.json").read_text(encoding="utf-8"))
        for case in evidence:
            self.assertFalse(set(case) & {"label", "reason", "y_pred", "eligible", "reference_id"})
            self.assertIn("source-0", case["current_groups"])
            self.assertEqual(len(case["next_overlapping_groups"]), 1)
        with (paths[0] / "reviewer/annotations.csv").open(encoding="utf-8", newline="") as stream:
            annotations = list(csv.DictReader(stream))
        self.assertEqual(len(annotations), 4)
        self.assertTrue(all(not r["human_label"] and not r["confidence"] and not r["rationale"] for r in annotations))
        key = json.loads((paths[0] / "coordinator/answer_key.json").read_text(encoding="utf-8"))
        self.assertEqual([r["label"] for r in key], ["stable", "stable"])
        with self.assertRaises(FileExistsError):
            prepare_review(self.forecast, self.source, self.source, paths[0], self.artifacts)

    def test_review_rejects_bad_options_paths_and_mismatched_sources(self):
        for options in ({"per_stratum": 0}, {"seed": -1}, {"per_stratum": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                prepare_review(self.forecast, self.source, self.source, self.artifacts / "review", self.artifacts, **options)
        with self.assertRaises(ValueError):
            prepare_review(self.forecast, self.source, self.source, self.root / "outside", self.artifacts)
        with self.assertRaisesRegex(ValueError, "immutable"):
            prepare_review(self.forecast, self.source, self.source, self.source / "nested-review", self.artifacts)
        # Produce another valid cohort; matching names/months are insufficient.
        with contextlib.redirect_stdout(io.StringIO()):
            other = run_preparation(load_config(self.config_path, run_id="other"), corpora=("moderatepolitics",))
        with self.assertRaisesRegex(ValueError, "differ|mismatch"):
            prepare_review(self.forecast, other, other, self.artifacts / "review", self.artifacts)

    def test_demo_cli_raw_and_replay_produce_verified_reports(self):
        args = ["week1", "--config", str(self.config_path), "--run-id", "demo",
                "--start", "2015-01", "--end", "2015-04", "--test-start", "2015-03", "--corpus", "moderatepolitics"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
        output = self.artifacts / "core/demo"
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["mode"], "raw_rebuild")
        self.assertEqual(manifest["status"], "complete")
        read_handoff(output / "forecast")
        with contextlib.redirect_stdout(io.StringIO()):
            replay = run_demo(self.config_path, "replay", graph_run=self.source, detection_run=self.source, test_start="2015-03")
        self.assertEqual(json.loads((replay / "manifest.json").read_text(encoding="utf-8"))["mode"], "verified_replay")
        with self.assertRaises((FileExistsError, ValueError)):
            run_demo(self.config_path, "demo")

    def test_demo_rejects_partial_replay_and_records_stage_failure(self):
        with self.assertRaisesRegex(ValueError, "both"):
            run_demo(self.config_path, "bad", graph_run=self.source)
        self.assertFalse((self.artifacts / "core/bad").exists())
        with patch("reddit_sna.reporting.forecast.export_report", side_effect=OSError("simulated write failure")):
            with self.assertRaises(OSError):
                run_demo(self.config_path, "failure", graph_run=self.source, detection_run=self.source, test_start="2015-03")
        manifest = json.loads((self.artifacts / "core/failure/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["failure_type"], "OSError")

    def test_cli_reporting_review_and_status(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(["pipelines"]), 0)
        self.assertIn("week1 implemented", stream.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["forecast-report", "--run", str(self.forecast), "--output", str(self.artifacts / "report"), "--artifact-root", str(self.artifacts)]), 0)
            self.assertEqual(main(["review-labels", "--forecast-run", str(self.forecast), "--graph-run", str(self.source), "--detection-run", str(self.source), "--output", str(self.artifacts / "review"), "--artifact-root", str(self.artifacts)]), 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["forecast-report", "--run", str(self.forecast), "--output", str(self.root / "escape"), "--artifact-root", str(self.artifacts)]), 2)
