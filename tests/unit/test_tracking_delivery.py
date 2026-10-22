"""Tracking artifact contracts with declared event fixtures; no graph producers."""
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.benchmarks.scenarios import build_transitions
from reddit_sna.evaluation.tracking import evaluate_events
from reddit_sna.reporting.tracking_demo import load_tracking_demo, pool_predictions, read_tracking_run
from reddit_sna.reporting.tracking_outputs import INPUT_PINS, LABELS, SOURCE_RUNS, TRACKER_CONFIG, _write_evaluation, run_split


def js(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def table(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def seal(root):
    js(root / "manifest.json", {"files": {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
                                          for p in root.rglob("*") if p.is_file() and p.name != "manifest.json"}})


def fixture(root, split):
    """Declare perfect predictions for every six-event truth fixture, all 18 IDs."""
    root.mkdir()
    js(root / "tracker-config.json", TRACKER_CONFIG)
    summaries = {}
    prefix, seeds = ("dev", (11, 12, 13)) if split == "development" else ("eval", (101, 102, 103))
    for case in LABELS:
        for seed in seeds:
            dataset = f"{prefix}-{case}-easy-g{seed}"
            truthref, detectorref = "truth-" + dataset, "detector-" + dataset
            transitions = build_transitions(case, truthref)
            truth_events = [{"source_community_id": r.source.community_id, "event": r.event.value} for r in transitions.events]
            counts = Counter(row["event"] for row in truth_events)
            macro = sum(label in counts for label in LABELS) / 6
            for route, reference in (("truth_tracking", truthref), ("detector_tracking", detectorref)):
                path = root / "datasets" / dataset / route
                path.mkdir(parents=True)
                def group(g):
                    return g if route == "truth_tracking" else "det-" + g
                events = [{"reference_id": reference, "source_month": "2020-01", "source_community_id": group(r.source.community_id),
                           "target_month": "2020-02", "event": r.event.value} for r in transitions.events]
                links = [{"reference_id": reference, "source_month": "2020-01", "source_community_id": group(r.source.community_id),
                          "target_month": "2020-02", "target_community_id": group(r.target.community_id)} for r in transitions.links]
                table(path / "events.csv", ("reference_id", "source_month", "source_community_id", "target_month", "event"), events)
                table(path / "links.csv", ("reference_id", "source_month", "source_community_id", "target_month", "target_community_id"), links)
                predictions = [{"source_community_id": r["source_community_id"], "truth_event": r["event"], "predicted_event": r["event"], "status": "matched"} for r in truth_events]
                table(path / "event_predictions.csv", tuple(predictions[0]), predictions)
                metrics = [{"event": label, "precision": int(label in counts), "recall": int(label in counts), "f1": int(label in counts), "support": counts[label]} for label in LABELS]
                metrics.append({"event": "macro_f1", "precision": "", "recall": "", "f1": macro, "support": len(events)})
                table(path / "metrics.csv", ("event", "precision", "recall", "f1", "support"), metrics)
                columns = (*LABELS, *(("__unmatched__",) if route == "detector_tracking" else ()))
                table(path / "confusion_matrix.csv", ("truth_event", *columns), [{"truth_event": label, **{c: counts[label] if c == label else 0 for c in columns}} for label in LABELS])
                js(path / "tracker_diagnostics.json", {"link_count": len(links), "source_count": len(events)})
                if route == "detector_tracking":
                    table(path / "source_mapping.csv", ("truth_community_id", "detector_community_id", "jaccard", "status"),
                          [{"truth_community_id": r["source_community_id"], "detector_community_id": group(r["source_community_id"]), "jaccard": 1, "status": "matched"} for r in truth_events])
                    js(path / "mapping_diagnostics.json", {"unmatched_truth": [], "extra_detector": []})
            summaries[dataset] = {"truth_reference": truthref, "detector_reference": detectorref, "truth_macro_f1": macro,
                                  "detector_macro_f1": macro, "extra_detector": 0, "unmatched_truth": 0}
    js(root / "metadata.json", {"status": "complete", "schema_version": 1, "artifact_type": "synthetic-tracking-replay", "split": split,
                               "input_manifest_sha256": INPUT_PINS[split], "detector_seed": 0, "datasets": 18, "summaries": summaries,
                               "tracker_config_sha256": sha256((root / "tracker-config.json").read_bytes()).hexdigest()})
    seal(root)


class TrackingDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temporary.name)
        for split in INPUT_PINS:
            fixture(cls.base / split, split)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_qualified_sources_pool_without_id_collisions(self):
        demo = load_tracking_demo(self.base / "development", self.base / "evaluation")
        self.assertEqual(len(demo["predictions"]), 156)
        self.assertEqual(len(demo["per_class"]), 24)
        self.assertEqual(demo["errors"], [])
        self.assertTrue(all(row["pooled_macro_f1"] == 1 for row in demo["summary"]))
        self.assertAlmostEqual(demo["summary"][0]["mean_dataset_macro_f1"], 11 / 36)

    def test_duplicate_qualified_sample_rejected(self):
        row = {"dataset_id": "x", "truth_reference": "r", "source_month": "2020-01", "source_community_id": "A",
               "target_month": "2020-02", "truth_event": "stable", "predicted_event": "stable"}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pool_predictions([row, row])

    def test_missing_prediction_stays_in_support(self):
        rows = [{"dataset_id": "d", "truth_reference": "r", "source_month": "2020-01", "source_community_id": source,
                 "target_month": "2020-02", "truth_event": truth, "predicted_event": prediction}
                for source, truth, prediction in (("A", "stable", "stable"), ("B", "grow", "__unmatched__"))]
        result = pool_predictions(rows)
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["confusion_matrix"]["grow"]["__unmatched__"], 1)
        self.assertAlmostEqual(result["macro_f1"], 1 / 6)

    def test_hash_tampering_rejected(self):
        root = self.base / "development"
        path = root / "datasets/dev-grow-easy-g11/truth_tracking/events.csv"
        before = path.read_bytes()
        try:
            path.write_bytes(before + b"\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_tracking_run(root, split="development")
        finally:
            path.write_bytes(before)

    def test_rehashed_wrong_reference_rejected(self):
        root = self.base / "development"
        path = root / "datasets/dev-grow-easy-g11/detector_tracking/events.csv"
        before, manifest = path.read_bytes(), (root / "manifest.json").read_bytes()
        try:
            path.write_bytes(before.replace(b"detector-dev-grow", b"WRONG-dev-grow"))
            seal(root)
            with self.assertRaisesRegex(ValueError, "reference or month"):
                read_tracking_run(root, split="development")
        finally:
            path.write_bytes(before)
            (root / "manifest.json").write_bytes(manifest)

    def test_unlisted_payload_rejected(self):
        path = self.base / "development/unlisted.txt"
        try:
            path.write_text("unlisted")
            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                read_tracking_run(self.base / "development", split="development")
        finally:
            path.unlink()

    def test_wrong_input_pin_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "input pin"):
                run_split(Path(d) / "input", Path(d) / "output", run_id="new", split="development",
                          source_run=SOURCE_RUNS["development"], input_manifest_sha256="wrong")
            self.assertFalse((Path(d) / "output").exists())

    def test_truth_confusion_six_columns_and_existing_files_preserved(self):
        result = evaluate_events([{"source_community_id": "A", "event": "stable"}], [{"source_community_id": "A", "event": "stable"}])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _write_evaluation(root, result, allow_unmatched=False)
            before = (root / "event_predictions.csv").read_bytes()
            with (root / "confusion_matrix.csv").open(newline="", encoding="utf-8") as stream:
                self.assertEqual(next(csv.reader(stream)), ["truth_event", *LABELS])
            with self.assertRaises(FileExistsError):
                _write_evaluation(root, result, allow_unmatched=False)
            self.assertEqual((root / "event_predictions.csv").read_bytes(), before)

    def test_truth_missing_prediction_is_not_hidden_in_six_columns(self):
        result = evaluate_events([{"source_community_id": "A", "event": "stable"}], [])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "every source"):
                _write_evaluation(Path(d), result, allow_unmatched=False)
            self.assertEqual(list(Path(d).iterdir()), [])
