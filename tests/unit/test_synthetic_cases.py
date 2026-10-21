"""Independent tiny partitions for post-hoc case selection and descriptions."""

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.reporting import synthetic_cases as report


def metric(dataset="a", score="0.7", **changes):
    return dict({"dataset_id": dataset, "month": "2020-02", "split": "development", "detector_seed": "0",
                 "canonical": "True", "ami": score, "ami_status": "ok" if score else "degenerate_partition",
                 "ami_reason": "" if score else "truth_constant"}, **changes)


def snapshot():
    return {"nodes": ["a", "b", "c", "d", "i"], "edges": [("a", "b"), ("c", "d"), ("b", "c")],
            "truth": {"a": "A", "b": "A", "c": "A", "d": "K", "i": "K"},
            "predicted": {"a": "x", "b": "x", "c": "y", "d": "y"}}


class SyntheticCasesTests(unittest.TestCase):
    def test_selection_is_order_independent_ties_lexical_and_canonical_fixed(self):
        rows = [metric("b"), metric("a"), metric("diagnostic", "-0.8", detector_seed="1", canonical="False"),
                metric("eval", "-0.9", split="evaluation"), metric("null-b", ""), metric("null-a", "")]
        result = report.select_case_rows(rows)
        self.assertEqual(result, report.select_case_rows(list(reversed(rows))))
        self.assertEqual([r["metric"]["dataset_id"] for r in result], ["a", "null-a"])
        self.assertEqual(result[0]["tied_minimum_rows"], 2)
        self.assertEqual(report.select_case_rows([metric("negative", "-0.1"), metric()])[0]["metric"]["dataset_id"], "negative")

    def test_missing_null_case_does_not_invent_one(self):
        self.assertEqual([c["kind"] for c in report.select_case_rows([metric()])], ["hard"])

    def test_invalid_selection_or_missing_reason_rejected(self):
        for rows in ([metric(), metric()], [metric(canonical="False")], [metric(score="nan")],
                     [metric(score="", ami_reason="")], [metric(ami_status="failed")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                report.select_case_rows(rows)

    def test_counts_keep_isolate_and_pair_error_categories(self):
        d = report.describe_snapshot(snapshot())
        self.assertEqual((d["active_nodes"], d["assigned_nodes"], d["unassigned_nodes"]), (5, 4, 1))
        self.assertEqual((d["scored_pairs"], d["truth_same_pred_different_pairs"], d["truth_different_pred_same_pairs"]), (6, 2, 1))
        self.assertEqual(sum(r["users"] for r in d["contingency"]), 5)
        self.assertEqual([r["users"] for r in d["contingency"] if not r["assigned"]], [0, 1])
        blocks = d["edge_blocks"]
        self.assertEqual(sum(r["edges"] for r in blocks), 3)
        self.assertEqual([(r["edges"], r["possible_edges"], r["density"]) for r in blocks], [(1, 1, 1), (1, 4, .25), (1, 1, 1)])

    def test_label_renaming_and_order_do_not_change_pair_errors(self):
        s = snapshot()
        expected = report.describe_snapshot(s)
        s["predicted"] = {u: {"x": "ZZ", "y": "AA"}[g] for u, g in s["predicted"].items()}
        s["nodes"].reverse(); s["edges"] = [(b, a) for a, b in reversed(s["edges"])]
        actual = report.describe_snapshot(s)
        for key in ("active_nodes", "assigned_nodes", "scored_pairs", "truth_same_pred_different_pairs", "truth_different_pred_same_pairs"):
            self.assertEqual(expected[key], actual[key])

    def test_same_partition_with_different_ids_has_no_pair_error(self):
        s = snapshot()
        s["predicted"] = {u: "renamed-" + s["truth"][u] for u in s["predicted"]}
        d = report.describe_snapshot(s)
        self.assertEqual((d["truth_same_pred_different_pairs"], d["truth_different_pred_same_pairs"]), (0, 0))

    def test_empty_graph_keeps_active_users_without_inventing_assignments(self):
        s = snapshot(); s["edges"] = []; s["predicted"] = {}
        d = report.describe_snapshot(s)
        self.assertEqual((d["assigned_nodes"], d["unassigned_nodes"], d["scored_pairs"]), (0, 5, 0))
        self.assertEqual(sum(r["users"] for r in d["contingency"]), 5)
        self.assertEqual(d["edge_blocks"], [])

    def test_invalid_keys_duplicate_edges_self_loop_or_assigned_isolate_rejected(self):
        for change in (lambda s: s["nodes"].append("a"), lambda s: s["truth"].pop("i"),
                       lambda s: s["predicted"].update(i="x"), lambda s: s["edges"].append(("b", "a")),
                       lambda s: s["edges"].append(("a", "a")), lambda s: s["edges"].append(("a", "outside"))):
            s = snapshot(); change(s)
            with self.subTest(s=s), self.assertRaises(ValueError):
                report.describe_snapshot(s)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "install [notebook]")
    def test_full_graph_and_user_contingency_display_counts_include_isolate(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.collections import PathCollection, LineCollection
        s = snapshot()
        c = {"kind": "hard", "dataset_id": "fixture", "month": "2020-02", "snapshot": s,
             "metric": metric(), "description": report.describe_snapshot(s)}
        figs = report.build_case_figures([c])
        self.addCleanup(lambda: [plt.close(f) for f in figs.values()])
        for ax in figs["hard"].axes[:2]:
            self.assertEqual(sum(len(p.get_offsets()) for p in ax.collections if isinstance(p, PathCollection)), 5)
            self.assertEqual(sum(len(p.get_segments()) for p in ax.collections if isinstance(p, LineCollection)), 3)
        self.assertEqual(int(figs["hard"].axes[2].images[0].get_array().sum()), 5)

    def test_null_summary_stays_missing_even_when_partition_disagrees(self):
        c = {"kind": "null", "split": "development", "dataset_id": "fixture", "month": "2020-02",
             "metric": dict(metric(score=""), coverage="1.0"), "description": report.describe_snapshot(snapshot()),
             "selection": "fixture", "tied_minimum_rows": None}
        row = report.case_summary([c])[0]
        self.assertIsNone(row["ami"])
        self.assertEqual(row["ami_reason"], "truth_constant")
        self.assertGreater(row["truth_same_pred_different_pairs"], 0)

    def test_export_existing_and_input_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / "bundle"; bundle.mkdir()
            for target in (bundle, bundle / "child", root):
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, "exists|overlaps"):
                    report.export_case_analysis({"bundle": bundle}, [], {}, target, notebook=root / "n")

    def test_publication_failure_retains_partial_without_complete_metadata(self):
        class BrokenFigure:
            def savefig(self, *args, **kwargs):
                raise OSError("simulated write error")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / "bundle"; bundle.mkdir()
            manifest = {"schema_version": 1, "status": "complete", "artifact_type": "phuc-dang-synthetic-data-handoff",
                        "source_manifest_sha256": {"development": "fixture", "evaluation": "fixture"}, "files": {}}
            path = bundle / "delivery-manifest.json"; path.write_text(json.dumps(manifest))
            demo = {"bundle": bundle, "delivery_sha256": sha256(path.read_bytes()).hexdigest()}
            c = {"kind": "hard", "split": "development", "dataset_id": "fixture", "month": "2020-02",
                 "metric": dict(metric(), coverage="1.0"), "description": report.describe_snapshot(snapshot()),
                 "selection": "fixture", "tied_minimum_rows": 1}
            out = root / "partial"
            with self.assertRaisesRegex(OSError, "simulated"):
                report.export_case_analysis(demo, [c], {"hard": BrokenFigure()}, out, notebook=root / "n")
            self.assertFalse((out / "metadata.json").exists())
            self.assertTrue((out / "analysis.json").exists())
            self.assertEqual(json.loads((out / "failure.json").read_bytes())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
