"""Numerical SNA, sensitivity and validation lifecycle tests on synthetic data."""

import importlib.util
import itertools
import json
import unittest
from unittest.mock import patch

from reddit_sna.config import load_config
from reddit_sna.data.archive import digest_file
from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.graphs.snapshots import write_csv
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.reporting.pilot import load_pilot
from reddit_sna.reporting.validation import (graph_from_rows, network_metrics, partition_comparison,
                                            analyze_networks, sensitivity, validate_pilot)
from tests.corpus_support import CorpusCase, record

HAS_GRAPH = importlib.util.find_spec("leidenalg") is not None


@unittest.skipUnless(HAS_GRAPH, "install [graph]")
class NetworkMetricTests(unittest.TestCase):
    def test_weighted_triangle_and_isolate_have_exact_metrics(self):
        rows = [{"source_user_id": u, "target_user_id": v, "weight": w}
                for u,v,w in (("a","b",1),("b","c",2),("a","c",3))]
        graph, _ = graph_from_rows(rows, ["a","b","c","isolate"])
        metrics = network_metrics(graph)
        self.assertEqual(metrics["components"], 2)
        self.assertEqual(metrics["largest_component_fraction_observed"], .75)
        self.assertEqual(metrics["degree_sum"], 6)
        self.assertEqual(metrics["strength_sum"], 12)
        self.assertEqual(metrics["density_observed_union"], .5)
        self.assertEqual(metrics["mean_strength"], 3)
        self.assertEqual(metrics["top_one_percent_strength_share"], 5/12)
        self.assertEqual(metrics["degree_distribution"], [(0,1),(2,3)])
        self.assertEqual(metrics["strength_distribution"], [(0,1),(3,1),(4,1),(5,1)])

    def test_empty_and_singleton_populations_remain_undefined(self):
        empty, _ = graph_from_rows([])
        one, _ = graph_from_rows([], ["only"])
        self.assertIsNone(network_metrics(empty)["largest_component_fraction_observed"])
        self.assertIsNone(network_metrics(one)["density_observed_union"])
        self.assertEqual(network_metrics(one)["isolates"], 1)
        self.assertIsNone(network_metrics(one)["top_one_percent_strength_share"])

    def test_invalid_weights_loops_and_duplicate_pairs_rejected(self):
        for edges in (("a","a",1), ("a","b",float("inf")), ("a","b",0)):
            with self.subTest(edges=edges), self.assertRaises(ValueError):
                graph_from_rows([dict(zip(("source_user_id","target_user_id","weight"), edges))])
        with self.assertRaises(ValueError):
            graph_from_rows([{"source_user_id":u,"target_user_id":v,"weight":1} for u,v in (("a","b"),("b","a"))])

    def test_partition_alignment_attrition_and_constant_policy(self):
        left = {"a":0,"b":0,"c":1,"d":1,"lost":2}
        same = {"a":9,"b":9,"c":3,"d":3}
        result = partition_comparison(left, same)
        self.assertEqual(result["common_user_ARI"], 1)
        self.assertEqual(result["baseline_support_retained"], .8)
        changed = partition_comparison(left, {"a":0,"b":1,"c":0,"d":1})
        self.assertLess(changed["common_user_ARI"], 0)
        for candidate in ({}, {"a":0}, {"a":0,"b":0,"c":0,"d":0}):
            self.assertIsNone(partition_comparison(left,candidate)["common_user_ARI"])


@unittest.skipUnless(HAS_GRAPH, "install [graph]")
class ValidationPipelineTests(CorpusCase):
    def pilot(self, *, future_only=False):
        self.raw([record("p", day="2015-04-01")] if future_only else None)
        run = run_preparation(load_config(self.config("core")), corpora=("moderatepolitics",))
        return run, load_pilot(self.root, run.name)

    def test_context_attribution_counts_and_empty_months(self):
        _, pilot = self.pilot()
        analysis = analyze_networks(pilot)
        jan, feb, march = analysis["months"]
        self.assertEqual(jan["strength_sum"], 4)
        self.assertEqual(jan["corpus_share_hhi"], 1)
        self.assertEqual(jan["corpus_event_shares"], {"moderatepolitics":1})
        self.assertEqual(jan["predeclared_contexts"]["moderatepolitics"]["strength_sum"],4)
        self.assertEqual(march["zero_support_corpora"],["moderatepolitics"])
        self.assertIsNone(feb["corpus_share_hhi"])

    def test_sensitivity_drop_count_empty_support_and_determinism(self):
        _, pilot = self.pilot()
        schedule = {"months":["2015-01","2015-02"], "gammas":[1.0],
                    "detector_seeds":[0], "edge_drop_fraction":.9, "drop_seeds":[100]}
        first = sensitivity(pilot, schedule)
        self.assertEqual(first, sensitivity(pilot, schedule))
        self.assertEqual(len(first["runs"]),4)
        self.assertTrue(first["runs"][0]["baseline_replay_partition_equal"])
        # A one-edge graph drops floor(.9 * 1)=0, explicitly recorded.
        self.assertEqual(first["runs"][1]["dropped_edges"],0)
        self.assertEqual(first["runs"][2]["baseline_users"],0)
        self.assertIsNone(first["runs"][2]["common_user_ARI"])

    def test_invalid_schedule_and_missing_month_rejected(self):
        _, pilot = self.pilot()
        base = {"months":["2015-01"], "gammas":[1], "detector_seeds":[0],
                "edge_drop_fraction":.05, "drop_seeds":[100]}
        for change in ({"edge_drop_fraction":1}, {"gammas":[-1]}, {"months":["2016-01"]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                sensitivity(pilot,{**base,**change})

    def test_validation_new_run_hashes_handoff_and_no_overwrite(self):
        run, _ = self.pilot()
        output = validate_pilot(self.root,run.name,"validated")
        manifest = json.loads((output/"manifest.json").read_text())
        self.assertEqual(manifest["status"],"complete")
        self.assertEqual(set(manifest["artifact_hashes"]),{"network_analysis.json","handoff.json"})
        self.assertIsNone(manifest["peak_memory_mb"])
        if importlib.util.find_spec("matplotlib"):
            from reddit_sna.reporting.figures import export_figures
            import matplotlib.pyplot as plt
            fig, _ = plt.subplots()
            self.addCleanup(plt.close,"all")
            exports = export_figures({"proof":fig},run.parent/"figures-proof",load_pilot(self.root,run.name),
                                      validation_runs=(output,))
            exported = json.loads((exports/"manifest.json").read_text())
            self.assertEqual(exported["validation_manifest_sha256"],{str(output):digest_file(output/"manifest.json")})
        with self.assertRaises(FileExistsError):
            validate_pilot(self.root,run.name,"validated")
        with self.assertRaises(ValueError):
            validate_pilot(self.root,run.name,"../escape")

    def test_failure_keeps_failed_status_and_partial_handoff(self):
        run, _ = self.pilot()
        with patch("reddit_sna.reporting.validation.analyze_networks",side_effect=RuntimeError("injected interruption")):
            with self.assertRaises(RuntimeError):
                validate_pilot(self.root,run.name,"failed-check")
        output = run.parent/"failed-check"
        manifest = json.loads((output/"manifest.json").read_text())
        self.assertEqual(manifest["status"],"failed")
        self.assertEqual(manifest["failure_type"],"RuntimeError")
        self.assertIn("handoff.json",manifest["artifact_hashes"])

    def test_all_future_pilot_and_extra_figures_are_truthful(self):
        _, pilot = self.pilot(future_only=True)
        analysis = analyze_networks(pilot)
        self.assertTrue(all(m["observed_users"]==0 for m in analysis["months"]))
        if importlib.util.find_spec("matplotlib"):
            from reddit_sna.reporting.validation_figures import build_validation_figures
            import matplotlib.pyplot as plt
            figures = build_validation_figures(analysis)
            self.addCleanup(plt.close,"all")
            self.assertEqual(len(figures),4)
            self.assertEqual(len(figures["10_degree_strength"].axes[0].lines), 0)

    def test_planted_disconnected_partition_adapter_recovers_truth(self):
        # This is a tiny adapter check, not the other pair's E2 research benchmark.
        source = self.root/"planted/2015-01"
        source.mkdir(parents=True)
        rows = [("2015-01",f"u{a}",f"u{b}",1) for block in (range(5),range(5,10))
                for a,b in itertools.combinations(block,2)]
        write_csv(source/"R.csv",["month","source_user_id","target_user_id","weight"],rows)
        result = detect_snapshots(source.parent,self.root/"partition","synthetic",seeds=(0,1,2))
        self.assertTrue(all(r["sizes"]==[5,5] for r in result["months"][0]["runs"]))
        from reddit_sna.reporting.pilot import read_csv
        members = read_csv(self.root/"partition/2015-01/membership-seed0.csv")
        truth = {f"u{i}":i//5 for i in range(10)}
        comparison = partition_comparison(truth,{r["user_id"]:r["community_id"] for r in members})
        self.assertEqual(comparison["common_user_ARI"],1)
        self.assertEqual(comparison["baseline_support_retained"],1)
        # Twenty unique edges means the frozen 5% policy drops exactly one.
        output = self.root/"partition"
        pilot = {"runs":{"graphs":source.parent.parent, "detection":output},
                 "graphs":{"actual_months":["2015-01"]}, "detection":result,
                 "manifests":{"detection":{"artifact_hashes":{
                     str(p.relative_to(output)):digest_file(p) for p in output.rglob("*.csv")}}}}
        # Place the graph in the public snapshots/<month> layout expected by analysis.
        import shutil
        snapshots = source.parent.parent/"snapshots"
        shutil.copytree(source.parent,snapshots)
        # detect_snapshots writes directly to output; public run layout has memberships/.
        member_root = self.root/"detector-run"
        member_root.mkdir()
        shutil.copytree(output,member_root/"memberships")
        pilot["runs"]["detection"] = member_root
        pilot["manifests"]["detection"]["artifact_hashes"] = {
            str(p.relative_to(member_root)):digest_file(p) for p in member_root.rglob("*.csv")}
        schedule = {"months":["2015-01"], "gammas":[1], "detector_seeds":[0],
                    "edge_drop_fraction":.05,"drop_seeds":[100]}
        checked = sensitivity(pilot,schedule)
        self.assertTrue(checked["runs"][0]["baseline_replay_partition_equal"])
        self.assertEqual(checked["runs"][1]["dropped_edges"],1)
        self.assertEqual(checked["runs"][1]["remaining_edges"],19)
        self.assertEqual(checked["runs"][1]["baseline_support_retained"],1)
        self.assertEqual(checked["runs"][1]["common_user_ARI"],1)
