"""Reporting policies with small independent fixtures, never benchmark producers."""

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from reddit_sna.reporting import synthetic_demo as report


def summary(**changes):
    row = {"split": "development", "aggregation_level": "all_scenarios", "scenario": "", "detector_seed": "0",
           "seed_role": "canonical", "n_rows": "6", "n_ami_valid": "5", "n_ami_missing": "1",
           "ami_mean": "0.5", "coverage_mean": "1.0", "ami_missing_reasons": '{"truth_constant":1}'}
    return dict(row, **changes)


def fixture_view():
    snapshots = [{"month": month, "nodes": ["a", "b", "c"], "edges": [("a", "b")],
                  "truth": {"a": "A", "b": "A", "c": "K"}, "predicted": {"a": "0", "b": "0"}}
                 for month in ("2020-01", "2020-02")]
    rows = []
    timing = []
    for split in ("development", "evaluation"):
        rows.extend(summary(split=split, aggregation_level="scenario", scenario=case) for case in report.SCENARIOS)
        rows.extend(summary(split=split, detector_seed=str(seed), seed_role="canonical" if seed == 0 else "diagnostic")
                    for seed in (0, 1, 2))
        timing.extend({"split": split, "phase": phase, "wall_seconds": 1.0, "scope": "fixture"}
                      for phase in ("generation", "detection", "evaluation"))
    return {"network": {"dataset_id": "tiny-contract-fixture", "snapshots": snapshots},
            "summary_view": report.summary_view(rows), "timings": timing}


class SyntheticDemoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-demo-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.data = self.bundle / "input.txt"
        self.data.write_bytes(b"immutable fixture\n")
        self.manifest = {"schema_version": 1, "status": "complete", "artifact_type": "phuc-dang-synthetic-data-handoff",
                         "source_manifest_sha256": {"development": "fixture", "evaluation": "fixture"},
                         "files": {"input.txt": {"sha256": sha256(self.data.read_bytes()).hexdigest(), "bytes": self.data.stat().st_size}}}
        self.pin = self.seal()

    def seal(self):
        path = self.bundle / "delivery-manifest.json"
        path.write_text(json.dumps(self.manifest), encoding="utf-8")
        return sha256(path.read_bytes()).hexdigest()

    def test_null_and_negative_scores_preserve_support(self):
        rows = report.summary_view([summary(ami_mean="-0.125"), summary(scenario="null-case", n_ami_valid="0", n_ami_missing="6", ami_mean="", coverage_mean="")])
        self.assertEqual(rows[0]["ami_mean"], -.125)
        self.assertIsNone(rows[1]["ami_mean"])
        self.assertIsNone(rows[1]["coverage_mean"])
        self.assertEqual(rows[1]["n_ami_missing"], 6)

    def test_invalid_support_or_duplicate_summary_rejected(self):
        for rows in ([summary(n_ami_missing="2")], [summary(n_rows="-1")], [summary(), summary()]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "support|duplicate"):
                report.summary_view(rows)

    def test_nonfinite_metric_and_inconsistent_mean_rejected(self):
        for value in ("nan", "inf", "-inf", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                report.summary_view([summary(ami_mean=value)])
        with self.assertRaisesRegex(ValueError, "mean/support"):
            report.summary_view([summary(n_ami_valid="0", n_ami_missing="6", ami_mean="1")])

    def test_canonical_is_not_reselected_by_larger_diagnostic_score(self):
        rows = report.summary_view([summary(ami_mean="0.1"), summary(detector_seed="1", seed_role="diagnostic", ami_mean="0.99")])
        self.assertEqual(next(r["detector_seed"] for r in rows if r["seed_role"] == "canonical"), 0)
        with self.assertRaisesRegex(ValueError, "canonical"):
            report.summary_view([summary(detector_seed="1", seed_role="canonical")])

    def test_timing_remains_original_all_seed_wrapper(self):
        manifest = {"stages": {p: {"wall_seconds": 9.0} for p in ("generation", "detection", "evaluation")},
                    "timing": {"stage_scope": "wrapper all three seeds", "run_scope": "recorded run", "run_wall_seconds": 30.0}}
        rows = report.timing_view(manifest, "development")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1]["wall_seconds"], 9.0)
        self.assertIn("all three seeds", rows[1]["scope"])
        self.assertEqual(rows[-1]["wall_seconds"], 30.0)

    def test_html_escapes_text_and_does_not_turn_null_into_zero(self):
        html = report.table_html([{"name": "<script>", "mean": None}])
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("—", html)
        self.assertNotIn("<script>", html)

    def test_delivery_pin_and_corruption_rejected(self):
        with self.assertRaisesRegex(ValueError, "manifest SHA"):
            report.verify_delivery(self.bundle, "0" * 64)
        self.data.write_bytes(b"changed\n")
        with self.assertRaisesRegex(ValueError, "file changed"):
            report.verify_delivery(self.bundle, self.pin)

    def test_recipient_check_directories_are_not_inputs(self):
        extra = self.bundle / "check-development-001"
        extra.mkdir()
        (extra / "not-a-source.txt").write_text("ignored")
        self.assertEqual(report.verify_delivery(self.bundle, self.pin), self.manifest)

    def test_pinned_manifest_cannot_escape_bundle(self):
        self.manifest["files"] = {"../outside.txt": self.manifest["files"]["input.txt"]}
        with self.assertRaisesRegex(ValueError, "unsafe delivery"):
            report.verify_delivery(self.bundle, self.seal())

    def test_missing_source_pin_or_failed_delivery_rejected(self):
        original = deepcopy(self.manifest)
        for mutate in (lambda m: m.update(status="failed"), lambda m: m["source_manifest_sha256"].pop("evaluation")):
            self.manifest = deepcopy(original)
            mutate(self.manifest)
            with self.assertRaises(ValueError):
                report.verify_delivery(self.bundle, self.seal())

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "install [notebook]")
    def test_full_display_keeps_all_nodes_edges_and_unassigned_isolate(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.collections import PathCollection, LineCollection
        figures = report.build_synthetic_figures(fixture_view())
        self.addCleanup(lambda: [plt.close(fig) for fig in figures.values()])
        self.assertEqual(len(figures), 4)
        for ax in figures["01_network"].axes:
            self.assertEqual(sum(len(c.get_offsets()) for c in ax.collections if isinstance(c, PathCollection)), 3)
            self.assertEqual(sum(len(c.get_segments()) for c in ax.collections if isinstance(c, LineCollection)), 1)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "install [notebook]")
    def test_all_null_case_is_gap_with_support_not_zero_bar(self):
        import matplotlib.pyplot as plt
        demo = fixture_view()
        for row in demo["summary_view"]:
            if row["level"] == "scenario" and row["scenario"] == "dissolve":
                row.update(ami_mean=None, n_ami_valid=0, n_ami_missing=6)
        figures = report.build_synthetic_figures(demo)
        self.addCleanup(lambda: [plt.close(fig) for fig in figures.values()])
        heights = [bar.get_height() for bar in figures["02_quality"].axes[0].patches]
        self.assertEqual(sum(math.isnan(v) for v in heights), 2)

    def test_export_rejects_existing_output_and_overlap_without_writes(self):
        output = self.root / "existing"
        output.mkdir()
        for target in (output, self.bundle / "child"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "exists|overlaps"):
                report.export_synthetic_demo({"bundle": self.bundle}, {}, target, notebook=self.data)
        self.assertEqual(list(output.iterdir()), [])

    def test_failed_figure_publication_retains_partial_and_no_complete_metadata(self):
        class BrokenFigure:
            def savefig(self, *args, **kwargs):
                raise OSError("simulated figure write error")
        figures = dict.fromkeys(("01_network", "02_quality", "03_seeds", "04_timing"), BrokenFigure())
        demo = {"bundle": self.bundle, "delivery_sha256": self.pin,
                "metrics": [{"fixture": "data"}], "summaries": [{"fixture": "data"}],
                "summary_view": [{"fixture": "data"}], "timings": [{"fixture": "data"}]}
        output = self.root / "partial"
        with self.assertRaisesRegex(OSError, "simulated"):
            report.export_synthetic_demo(demo, figures, output, notebook=self.data)
        self.assertFalse((output / "metadata.json").exists())
        self.assertEqual(json.loads((output / "failure.json").read_bytes())["status"], "failed")
        self.assertTrue((output / "tables/metrics.csv").is_file())


if __name__ == "__main__":
    unittest.main()
