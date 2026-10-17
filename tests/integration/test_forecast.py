"""Full synthetic preparation-to-forecast handoff with real file integrity."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch
import csv

from reddit_sna.cli import main
from reddit_sna.config import load_config
from reddit_sna.data.archive import digest_file
from reddit_sna.pipelines.forecast import run_forecast
from reddit_sna.pipelines.preparation import run_preparation
from tests.corpus_support import CorpusCase, record


class ForecastIntegrationTests(CorpusCase):
    def run_forecast(self, **overrides):
        args = dict(graph_run=self.source, detection_run=self.source,
                    artifact_root=self.root / "artifacts", output=self.output, test_start="2015-03")
        args.update(overrides)
        return run_forecast(**args)

    def test_separate_graph_and_detection_handoff(self):
        config = load_config(self.config("core"), run_id="separate-detection")
        detection = run_preparation(config, stage="detect", source_run=self.source)
        self.run_forecast(detection_run=detection)
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["status"], "complete")

    def test_invalid_options_and_missing_input_leave_no_output(self):
        for options in ({"threshold": 0}, {"threshold": float("nan")},
                        {"test_start": "2016-01"}, {"test_start": "2015-02"},
                        {"test_start": "bad"}, {"seed": -1},
                        {"graph_run": self.root / "missing"},
                        {"output": self.root / "outside-artifacts"}):
            with self.subTest(options=options), self.assertRaises((ValueError, OSError)):
                self.run_forecast(**options)
            self.assertFalse(self.output.exists())
        self.assertFalse((self.root / "outside-artifacts").exists())

    def test_source_manifest_changed_during_read_is_rejected(self):
        from reddit_sna.reporting.handoff import inspect_handoff
        calls = 0
        def change_after_second_read(*args):
            nonlocal calls
            result = inspect_handoff(*args)
            calls += 1
            if calls == 2:
                with (self.source / "manifest.json").open("a") as stream:
                    stream.write(" ")
            return result
        with patch("reddit_sna.pipelines.forecast.inspect_handoff", side_effect=change_after_second_read):
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                self.run_forecast()
        self.assertFalse(self.output.exists())

    def test_missing_calendar_month_is_rejected_before_membership_read(self):
        acceptance = {"months": [{"month": "2015-01"}, {"month": "2015-03"}]}
        with patch("reddit_sna.pipelines.forecast.inspect_handoff", return_value=acceptance):
            with self.assertRaisesRegex(ValueError, "consecutive"):
                self.run_forecast()
        self.assertFalse(self.output.exists())

    def test_write_failure_records_failed_manifest_without_overwriting_source(self):
        original = digest_file(self.source / "manifest.json")
        with patch("reddit_sna.pipelines.forecast._write", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.run_forecast()
        failure = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(failure["status"], "failed")
        self.assertEqual(failure["failure_type"], "OSError")
        self.assertEqual(digest_file(self.source / "manifest.json"), original)
        with self.assertRaises(FileExistsError):
            self.run_forecast()

    def test_reproducible_files_and_no_last_month_label(self):
        self.run_forecast()
        second = self.output.with_name("forecast-repeat")
        self.run_forecast(output=second)
        for name in ("samples.csv", "tracking.csv", "predictions.csv", "metrics.json"):
            self.assertEqual((self.output / name).read_bytes(), (second / name).read_bytes())
        with (self.output / "samples.csv").open() as stream:
            samples = list(csv.DictReader(stream))
        self.assertEqual([r["feature_month"] for r in samples], ["2015-01", "2015-02"])
        self.assertEqual({r["label"] for r in samples}, {"stable"})
        for row in samples:
            self.assertEqual(float(row["size"]), 2)
            self.assertEqual(float(row["internal_weight"]), 1)
            self.assertEqual(float(row["density"]), 1)

    def test_ged_history_exports_are_consumable_without_model_loading(self):
        from reddit_sna.reporting.forecast_handoff import read_handoff
        self.run_forecast(tracker="ged", history=True)
        handoff = read_handoff(self.output)
        self.assertEqual(len(handoff["features"]), 3)
        self.assertEqual(len(handoff["labels"]), 2)
        self.assertEqual([float(r["community_age"]) for r in handoff["features"]], [1, 2, 3])
        self.assertEqual([r["history_missing"] for r in handoff["features"]], ["1", "0", "0"])
        self.assertTrue((self.output / "inclusion_pairs.csv").exists())
        self.assertEqual(handoff["manifest"]["tracker"], "ged-strength-topology-v1")
        import joblib
        model = joblib.load(self.output / "majority.joblib")
        sample = handoff["features"][1]
        self.assertEqual(model.predict([[float(sample[f]) for f in handoff["manifest"]["features"]]])[0], "stable")

    def test_consumer_detects_resealed_join_corruption(self):
        from reddit_sna.reporting.forecast_handoff import read_handoff
        self.run_forecast(tracker="ged", history=True)
        sample_file = self.output / "samples.csv"
        with sample_file.open() as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        rows[0]["size"] = "9999"
        with sample_file.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        manifest_path = self.output / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["artifact_hashes"]["samples.csv"] = digest_file(sample_file)
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "differ"):
            read_handoff(self.output)

    def test_consumer_rejects_incomplete_run_and_missing_inventory(self):
        from reddit_sna.reporting.forecast_handoff import read_handoff
        self.run_forecast()
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text())
        for change in ({"status": "failed"}, {"artifact_hashes": {}}):
            path.write_text(json.dumps({**manifest, **change}))
            with self.assertRaises(ValueError):
                read_handoff(self.output)

    def test_future_month_append_preserves_all_past_ged_history_features(self):
        from reddit_sna.reporting.forecast_handoff import read_handoff
        self.run_forecast(tracker="ged", history=True)
        before = read_handoff(self.output)
        rows = [record("p", "A", day="2014-12-01")]
        rows.extend(record(f"r{m}", "B", parent="p", day=f"2015-{m:02d}-02") for m in range(1, 5))
        self.raw(rows)
        source = run_preparation(load_config(self.config("core"), run_id="appended"),
                                 corpora=("moderatepolitics",), end="2015-05")
        after_path = self.output.with_name("appended-forecast")
        self.run_forecast(graph_run=source, detection_run=source, output=after_path, tracker="ged", history=True)
        after = read_handoff(after_path)
        fields = ["feature_month", "community_id"] + before["manifest"]["features"]
        normalize = lambda rows: [{f: r[f] for f in fields} for r in rows if r["feature_month"] <= "2015-03"]
        self.assertEqual(normalize(before["features"]), normalize(after["features"]))

    def test_empty_middle_month_is_not_skipped_or_joined_across(self):
        rows = [record("p", "A", day="2014-12-01"),
                record("jan", "B", parent="p", day="2015-01-02"),
                record("mar", "B", parent="p", day="2015-03-02"),
                record("apr", "B", parent="p", day="2015-04-02")]
        self.raw(rows)
        config = load_config(self.config("core"), run_id="empty-middle")
        source = run_preparation(config, corpora=("moderatepolitics",), end="2015-05")
        self.run_forecast(graph_run=source, detection_run=source, test_start="2015-04")
        with (self.output / "samples.csv").open() as stream:
            samples = list(csv.DictReader(stream))
        self.assertEqual([(r["feature_month"], r["label_month"], r["label"]) for r in samples],
                         [("2015-01", "2015-02", "dissolve"), ("2015-03", "2015-04", "stable")])

    def test_empty_final_month_keeps_previous_source_label(self):
        from reddit_sna.reporting.forecast_handoff import read_handoff
        source = run_preparation(load_config(self.config("core"), run_id="empty-final"),
                                 corpora=("moderatepolitics",), end="2015-05")
        self.run_forecast(graph_run=source, detection_run=source, tracker="ged", history=True)
        handoff = read_handoff(self.output)
        self.assertEqual(len(handoff["features"]), 3)
        self.assertEqual(len(handoff["labels"]), 3)
        self.assertEqual(handoff["labels"][-1]["label_month"], "2015-04")
        self.assertEqual(handoff["labels"][-1]["label"], "dissolve")

    def setUp(self):
        super().setUp()
        rows = [record("p", "A", day="2014-12-01")]
        rows.extend(record(f"r{m}", "B", parent="p", day=f"2015-{m:02d}-02")
                    for m in range(1, 4))
        self.raw(rows)
        with contextlib.redirect_stdout(io.StringIO()):
            self.source = run_preparation(load_config(self.config("core")), corpora=("moderatepolitics",))
        self.output = self.root / "artifacts" / "forecast-001"

    def test_cli_outputs_verified_models_and_cannot_overwrite(self):
        args = ["forecast", "--graph-run", str(self.source), "--detection-run", str(self.source),
                "--artifact-root", str(self.root / "artifacts"), "--output", str(self.output),
                "--test-start", "2015-03"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
        manifest = json.loads((self.output / "manifest.json").read_text())
        for path, expected in manifest["artifact_hashes"].items():
            self.assertEqual(digest_file(self.output / path), expected)
        import joblib
        model = joblib.load(self.output / "majority.joblib")
        self.assertEqual(model.predict([[2, 1, 1, 0, 1]])[0], "stable")
        metrics = json.loads((self.output / "metrics.json").read_text())
        self.assertEqual((metrics["train_samples"], metrics["test_samples"]), (1, 1))
        before = digest_file(self.output / "manifest.json")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 2)
        self.assertEqual(digest_file(self.output / "manifest.json"), before)

    def test_corruption_rejected_before_output_creation(self):
        with (self.source / "detection.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            run_forecast(self.source, self.source, self.root / "artifacts", self.output, "2015-03")
        self.assertFalse(self.output.exists())
