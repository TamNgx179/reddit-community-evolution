"""Persisted evaluation report, provenance, timing and no-overwrite checks."""
import csv
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import unittest

from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset
from reddit_sna.evaluation.detection import export_detection_evaluation
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("igraph", "leidenalg", "sklearn")), "install [graph,evaluation] for report fixtures")
class DetectionReportExportTests(ProjectCase):
    def pair(self, scenario="stable", *, zero=False, isolates=False):
        config = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        if zero:
            config["generator"].update(p_in=0, p_out=0)
        if isolates:
            config["generator"].update(p_in=0.05, p_out=0)
        source, detected = self.root / (scenario + "-source"), self.root / (scenario + "-detected")
        export_graph_dataset(source, benchmark=config, scenario=scenario, generator_seed=11)
        export_synthetic_detection(source, detected)
        return source, detected

    @staticmethod
    def rows(path):
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def files(directory):
        return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}

    @staticmethod
    def write_rows(path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_rehashed_prediction_csv_still_rejects_duplicate_missing_unknown_and_isolate_users(self):
        source, detected = self.pair(isolates=True)
        relative = "memberships/2020-01/membership-seed0.csv"
        path, meta_path = detected / relative, detected / "metadata.json"
        original_rows, original_meta = self.rows(path), json.loads(meta_path.read_text())
        active = {row["user_id"] for row in self.rows(source / "snapshots/2020-01/nodes.csv")}
        assigned = {row["user_id"] for row in original_rows}
        self.assertTrue(assigned and active - assigned, "fixture needs endpoints and isolates")
        cases = {
            "duplicate": (original_rows + original_rows[:1], "duplicate membership"),
            "missing": (original_rows[1:], "missing expected users"),
            "unknown": (original_rows + [{**original_rows[0], "user_id": "outside"}], "unexpected user"),
            "isolate": (original_rows + [{**original_rows[0], "user_id": sorted(active - assigned)[0]}], "unexpected user"),
        }
        for case, (rows, reason) in cases.items():
            self.write_rows(path, rows)
            meta = json.loads(json.dumps(original_meta))
            digest = sha256(path.read_bytes()).hexdigest()
            meta["files"][relative]["sha256"] = digest
            for entry in meta["memberships"]:
                if entry["path"] == relative:
                    entry["sha256"] = digest
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            before = [self.files(source), self.files(detected)]
            output = self.root / case
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, reason):
                export_detection_evaluation([(source, detected)], output)
            self.assertFalse(output.exists())
            self.assertEqual([self.files(source), self.files(detected)], before)

    def test_rehashed_truth_csv_still_rejects_duplicate_missing_and_unknown_users(self):
        source, detected = self.pair()
        relative = "truth/membership.csv"
        path = source / relative
        source_meta_path, detected_meta_path = source / "metadata.json", detected / "metadata.json"
        original_rows = self.rows(path)
        original_source_meta = json.loads(source_meta_path.read_text())
        original_detected_meta = json.loads(detected_meta_path.read_text())
        cases = {
            "duplicate": (original_rows + original_rows[:1], "duplicate membership"),
            "missing": (original_rows[1:], "missing expected users"),
            "unknown": (original_rows + [{**original_rows[0], "user_id": "outside"}], "unexpected user"),
        }
        for case, (rows, reason) in cases.items():
            self.write_rows(path, rows)
            source_meta = json.loads(json.dumps(original_source_meta))
            source_meta["files"][relative]["sha256"] = sha256(path.read_bytes()).hexdigest()
            source_meta_path.write_text(json.dumps(source_meta), encoding="utf-8")
            detected_meta = json.loads(json.dumps(original_detected_meta))
            detected_meta["source"]["files"]["metadata.json"]["sha256"] = sha256(source_meta_path.read_bytes()).hexdigest()
            detected_meta_path.write_text(json.dumps(detected_meta), encoding="utf-8")
            before = [self.files(source), self.files(detected)]
            output = self.root / case
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, reason):
                export_detection_evaluation([(source, detected)], output)
            self.assertFalse(output.exists())
            self.assertEqual([self.files(source), self.files(detected)], before)

    def test_final_metadata_rename_failure_does_not_publish_a_complete_report(self):
        pair, output = self.pair(), self.root / "unpublished"
        original_rename = Path.rename
        def fail_publishing(path, target):
            if path.name == "metadata.pending.json":
                raise OSError("final publication failure")
            return original_rename(path, target)
        with patch.object(Path, "rename", autospec=True, side_effect=fail_publishing), self.assertRaisesRegex(OSError, "final publication failure"):
            export_detection_evaluation([pair], output)
        self.assertFalse((output / "metadata.json").exists())
        self.assertEqual(json.loads((output / "failure.json").read_text())["status"], "failed")
        pending = json.loads((output / "metadata.pending.json").read_text())
        for name, info in pending["files"].items():
            self.assertEqual(sha256((output / name).read_bytes()).hexdigest(), info["sha256"])
        before = self.files(output)
        with self.assertRaises(ValueError):
            export_detection_evaluation([pair], output)
        self.assertEqual(self.files(output), before)

    def test_two_datasets_write_metrics_summary_policy_timing_and_verified_provenance(self):
        pairs = [self.pair("stable"), self.pair("grow")]
        before = [self.files(path) for pair in pairs for path in pair]
        output = self.root / "evaluation"
        meta = export_detection_evaluation(pairs, output)
        self.assertEqual(set(self.files(output)), {"detection_metrics.csv", "detection_summary.csv", "ami-policy.json", "timing.json", "metadata.json"})
        self.assertEqual((meta["status"], meta["dataset_count"], meta["metric_rows"], meta["summary_rows"]), ("complete", 2, 12, 9))
        self.assertEqual(meta["completed_stages"], ["evaluation"])
        for name, info in meta["files"].items():
            self.assertEqual(sha256((output / name).read_bytes()).hexdigest(), info["sha256"])
        rows = self.rows(output / "detection_metrics.csv")
        self.assertEqual(len({(r["dataset_id"], r["month"], r["detector_seed"]) for r in rows}), 12)
        self.assertTrue(all(r["ami_status"] == "ok" and float(r["ami"]) == 1 for r in rows))
        summary = self.rows(output / "detection_summary.csv")
        overall = [r for r in summary if r["aggregation_level"] == "all_scenarios"]
        self.assertEqual([(r["detector_seed"], r["n_rows"], r["n_ami_valid"], r["n_ami_missing"]) for r in overall],
                         [("0", "4", "4", "0"), ("1", "4", "4", "0"), ("2", "4", "4", "0")])
        timing = json.loads((output / "timing.json").read_text())
        self.assertEqual(len(timing["detection_by_month"]), 4)
        expected = sum(month["wall_seconds"] for _, detected in pairs
                       for month in json.loads((detected / "detection.json").read_text())["months"])
        self.assertEqual(timing["detection_wall_seconds"], expected)
        self.assertIsNone(timing["generation_wall_seconds"])
        self.assertIsNone(timing["peak_memory_bytes"])
        self.assertGreaterEqual(timing["evaluation_wall_seconds"], timing["evaluation_compute_wall_seconds"])
        self.assertEqual([self.files(path) for pair in pairs for path in pair], before)

    def test_all_missing_ami_stays_blank_in_csv_with_reason_and_support(self):
        output = self.root / "empty-report"
        export_detection_evaluation([self.pair(zero=True)], output)
        self.assertTrue(all(row["ami"] == "" and row["ami_status"] == "empty_scored" and row["coverage"] == "0.0"
                            for row in self.rows(output / "detection_metrics.csv")))
        self.assertTrue(all(row["ami_mean"] == "" and row["n_ami_valid"] == "0" and row["n_ami_missing"] == "2"
                            and row["coverage_mean"] == "0.0" for row in self.rows(output / "detection_summary.csv")))

    def test_cli_replay_is_deterministic_and_existing_output_is_never_overwritten(self):
        pairs = [self.pair("stable"), self.pair("grow")]
        first, second = self.root / "first", self.root / "second"
        export_detection_evaluation(pairs, first)
        command = [sys.executable, "-m", "reddit_sna.evaluation.detection", "--output", str(second)]
        for source, detected in reversed(pairs):
            command += ["--pair", str(source), str(detected)]
        replay = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout)["metric_rows"], 12)
        for name in ("detection_metrics.csv", "detection_summary.csv", "ami-policy.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        before = self.files(second)
        repeat = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(repeat.returncode, 2)
        self.assertEqual(self.files(second), before)

    def test_duplicate_ids_overlap_existing_or_invalid_input_fail_before_output(self):
        pair = self.pair()
        output = self.root / "invalid"
        for invalid in ([], [pair, pair], [(pair[0], self.root / "missing")], ["bad"], [(pair[0], pair[0])]):
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, OSError)):
                export_detection_evaluation(invalid, output)
            self.assertFalse(output.exists())
        with self.assertRaises(ValueError):
            export_detection_evaluation([pair], pair[0] / "nested")
        self.assertFalse((pair[0] / "nested").exists())
        output.mkdir()
        with self.assertRaises(ValueError):
            export_detection_evaluation([pair], output)
        self.assertEqual(list(output.iterdir()), [])

    def test_rehashed_but_invalid_timing_diagnostics_fail_before_output(self):
        source, detected = self.pair()
        path, meta_path = detected / "detection.json", detected / "metadata.json"
        original, original_meta = json.loads(path.read_text()), json.loads(meta_path.read_text())
        cases = ("negative", "bool", "nan", "missing-month", "wrong-cohort", "wrong-seeds", "duplicate-run", "wrong-run-ref")
        for case in cases:
            data, meta = json.loads(json.dumps(original)), json.loads(json.dumps(original_meta))
            if case in ("negative", "bool", "nan"):
                data["months"][0]["wall_seconds"] = {"negative": -1, "bool": True, "nan": float("nan")}[case]
            elif case == "missing-month": data["months"].pop()
            elif case == "wrong-cohort": data["graph_reference"] = "other"
            elif case == "wrong-seeds": data["detector_seeds"] = [0, True, 2]
            elif case == "duplicate-run": data["months"][0]["runs"][1] = data["months"][0]["runs"][0]
            else: data["months"][0]["runs"][0]["reference_id"] = "other"
            path.write_text(json.dumps(data), encoding="utf-8")
            meta["files"]["detection.json"]["sha256"] = sha256(path.read_bytes()).hexdigest()
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            with self.subTest(case=case), self.assertRaises(ValueError):
                export_detection_evaluation([(source, detected)], self.root / case)
            self.assertFalse((self.root / case).exists())

    def test_publication_failure_keeps_partial_files_without_complete_metadata(self):
        pair, output = self.pair(), self.root / "failed"
        with patch("reddit_sna.evaluation.detection._write_report_csv", side_effect=OSError("disk failure")), self.assertRaisesRegex(OSError, "disk failure"):
            export_detection_evaluation([pair], output)
        self.assertTrue((output / "ami-policy.json").is_file())
        self.assertFalse((output / "metadata.json").exists())
        failure = json.loads((output / "failure.json").read_text())
        self.assertEqual((failure["status"], failure["error_type"]), ("failed", "OSError"))

    def test_input_change_during_scoring_is_rejected_before_output(self):
        from reddit_sna.evaluation.detection import score_snapshot
        source, detected = self.pair()
        original = (source / "truth/events.csv").read_bytes()
        changed = False
        def changing_score(frame):
            nonlocal changed
            if not changed:
                (source / "truth/events.csv").write_bytes(original + b"\n")
                changed = True
            return score_snapshot(frame)
        with patch("reddit_sna.evaluation.detection.score_snapshot", side_effect=changing_score), self.assertRaises(ValueError):
            export_detection_evaluation([(source, detected)], self.root / "changed")
        self.assertFalse((self.root / "changed").exists())
