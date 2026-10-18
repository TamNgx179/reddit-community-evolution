"""Read persisted graph/truth and Leiden packages for identity-safe alignment."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import unittest

from reddit_sna.benchmarks.config import load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset
from reddit_sna.evaluation.detection import load_aligned_detection
from reddit_sna.pipelines.detection_tracking import export_synthetic_detection
from tests.support import ProjectCase

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(importlib.util.find_spec("igraph") and importlib.util.find_spec("leidenalg"), "install [graph] for alignment fixtures")
class DetectionPackageAlignmentTests(ProjectCase):
    def pair(self, *, zero_edges=False):
        benchmark = load_benchmark_config(ROOT / "configs/benchmark_week1.json")
        if zero_edges:
            benchmark["generator"].update(p_in=0, p_out=0)
        source, predicted = self.root / "source", self.root / "detected"
        export_graph_dataset(source, benchmark=benchmark, scenario="stable", generator_seed=11)
        export_synthetic_detection(source, predicted)
        return source, predicted

    @staticmethod
    def files(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    @staticmethod
    def write_meta(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_all_three_seeds_load_and_input_relocation_preserves_vectors_without_writes(self):
        source, predicted = self.pair()
        before_source, before_predicted = self.files(source), self.files(predicted)
        results = [load_aligned_detection(source, predicted, detector_seed=seed) for seed in (0, 1, 2)]
        for seed, result in enumerate(results):
            self.assertEqual(result.dataset_id, "dev-stable-easy-g11")
            self.assertEqual(result.identity_scope, result.dataset_id)
            self.assertEqual(result.difficulty, "easy")
            self.assertEqual(result.detector_seed, seed)
            self.assertTrue(result.detector_reference.endswith(f"-seed{seed}"))
            self.assertEqual([s.month for s in result.snapshots], ["2020-01", "2020-02"])
            for frame in result.snapshots:
                self.assertEqual(len(frame.user_ids), 24)
                self.assertEqual(frame.user_ids, frame.active_user_ids)
                self.assertEqual(len(frame.truth_labels), len(frame.predicted_labels))
                self.assertEqual(frame.user_ids, tuple(sorted(frame.user_ids)))
        moved_source, moved_predicted = self.root / "moved source", self.root / "moved detected"
        shutil.copytree(source, moved_source)
        shutil.copytree(predicted, moved_predicted)
        self.assertEqual(load_aligned_detection(moved_source, moved_predicted), results[0])
        self.assertEqual(self.files(source), before_source)
        self.assertEqual(self.files(predicted), before_predicted)

    def test_wrong_dataset_reference_month_seed_or_mapping_is_rejected(self):
        source, predicted = self.pair()
        path = predicted / "metadata.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        cases = (
            ("dataset_id", "other"), ("identity_scope", "other"), ("truth_reference", "truth-other"),
            ("observed_months", ["2020-01"]), ("graph_protocol", "reddit"), ("membership_schema_version", True),
            ("scope", "forecast"), ("completed_stages", []), ("diagnostics_schema_version", True),
            ("memberships", original["memberships"][:-1]),
        )
        for key, value in cases:
            bad = {**original, key: value}
            self.write_meta(path, bad)
            before = self.files(predicted)
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_aligned_detection(source, predicted)
            self.assertEqual(self.files(predicted), before)
        for kind in ("seed-reference", "duplicate-mapping", "month-graph", "path"):
            bad = json.loads(json.dumps(original))
            if kind == "seed-reference":
                bad["detector_references"]["1"] = bad["detector_references"]["0"]
            elif kind == "duplicate-mapping":
                bad["memberships"][-1] = bad["memberships"][0]
            elif kind == "month-graph":
                bad["memberships"][0]["graph_sha256"] = "0" * 64
            else:
                bad["memberships"][0]["path"] = "../outside.csv"
            self.write_meta(path, bad)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                load_aligned_detection(source, predicted)
        self.write_meta(path, original)
        for seed in (True, 3, "0", -1):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                load_aligned_detection(source, predicted, detector_seed=seed)

    def test_truth_or_prediction_hash_corruption_is_rejected_without_mutation(self):
        source, predicted = self.pair()
        for path in (source / "truth/membership.csv", predicted / "memberships/2020-01/membership-seed0.csv"):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            before_source, before_predicted = self.files(source), self.files(predicted)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_aligned_detection(source, predicted)
            self.assertEqual(self.files(source), before_source)
            self.assertEqual(self.files(predicted), before_predicted)
            path.write_bytes(original)

    def test_rehashed_source_graph_still_cannot_reuse_an_old_detector_cohort(self):
        source, predicted = self.pair()
        graph = source / "snapshots/2020-01/R.csv"
        graph.write_bytes(b"".join(graph.read_bytes().splitlines(keepends=True)[:-1]))
        relative = "snapshots/2020-01/R.csv"
        digest = sha256(graph.read_bytes()).hexdigest()
        truth_path, pred_path = source / "metadata.json", predicted / "metadata.json"
        truth_meta = json.loads(truth_path.read_text(encoding="utf-8"))
        truth_meta["files"][relative]["sha256"] = digest
        truth_meta["counts"]["edges_by_month"]["2020-01"] -= 1
        self.write_meta(truth_path, truth_meta)
        pred_meta = json.loads(pred_path.read_text(encoding="utf-8"))
        pred_meta["source"]["files"][relative]["sha256"] = digest
        pred_meta["source"]["files"]["metadata.json"]["sha256"] = sha256(truth_path.read_bytes()).hexdigest()
        self.write_meta(pred_path, pred_meta)
        with self.assertRaisesRegex(ValueError, "graph cohort reference mismatch"):
            load_aligned_detection(source, predicted)

    def test_empty_endpoint_graph_keeps_all_truth_but_has_empty_scored_vectors(self):
        source, predicted = self.pair(zero_edges=True)
        result = load_aligned_detection(source, predicted)
        self.assertEqual(len(result.snapshots), 2)
        for frame in result.snapshots:
            self.assertEqual(len(frame.active_user_ids), 24)
            self.assertEqual(len(frame.truth_labels_all), 24)
            self.assertEqual(frame.user_ids, ())
            self.assertEqual(frame.truth_labels, ())
            self.assertEqual(frame.predicted_labels, ())
