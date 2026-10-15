"""Exercise reporting on temporary synthetic runs, never private Reddit data."""

from dataclasses import replace
import builtins
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from reddit_sna.config import load_config
from reddit_sna.data.archive import digest_file
from reddit_sna.pipelines.preparation import run_preparation
from reddit_sna.reporting.pilot import load_pilot, resolve_runs, verified_manifest
from reddit_sna.reporting.figures import corpus_matrix, sample_network, plotting_dependencies
from tests.corpus_support import CorpusCase, record

HAS_GRAPH = importlib.util.find_spec("leidenalg") is not None
HAS_PLOTS = importlib.util.find_spec("matplotlib") is not None


@unittest.skipUnless(HAS_GRAPH, "install [graph]")
class ReportingTests(CorpusCase):
    def pilot_run(self, *, separate=False, empty=False):
        """Build tiny real pipeline artifacts; empty months remain in the cohort."""
        self.raw([record("p", day="2015-04-01")] if empty else None)
        config = load_config(self.config("core"))
        if separate:
            normalized = run_preparation(config, stage="normalize", corpora=("moderatepolitics",))
            graphs = run_preparation(replace(config, run_id="graphs"), stage="snapshots", source_run=normalized)
            return run_preparation(replace(config, run_id="detection"), stage="detect", source_run=graphs)
        return run_preparation(config, corpora=("moderatepolitics",))

    @staticmethod
    def reseal(run, relative, value):
        """Re-seal deliberately wrong summaries to test semantic validation."""
        (run / relative).write_text(json.dumps(value), encoding="utf-8")
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["artifact_hashes"][relative] = digest_file(run / relative)
        (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_all_stage_replay_and_zero_cells(self):
        run = self.pilot_run()
        pilot = load_pilot(self.root, run.name)
        self.assertEqual(set(pilot["runs"].values()), {run})
        corpora, months, matrix = corpus_matrix(pilot["graphs"])
        self.assertEqual(corpora, ["moderatepolitics"])
        self.assertEqual(months, ["2015-01", "2015-02", "2015-03"])
        self.assertEqual(matrix, [[2, 0, 0]])

    def test_separate_source_chain_replay_preserves_inputs(self):
        original = self.marker.read_bytes()
        run = self.pilot_run(separate=True)
        pilot = load_pilot(self.root, run.name)
        self.assertEqual(len(set(pilot["runs"].values())), 3)
        self.assertEqual(self.marker.read_bytes(), original)

    def test_missing_and_ambiguous_candidate_selection(self):
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            resolve_runs(self.root)
        run = self.pilot_run()
        self.assertEqual(resolve_runs(self.root)["detection"], run)
        other = run.parent / "other"
        other.mkdir()
        (other / "detection.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "explicitly"):
            resolve_runs(self.root)
        self.assertEqual(resolve_runs(self.root, run.name)["detection"], run)

    def test_corrupted_artifact_rejected(self):
        run = self.pilot_run()
        with (run / "detection.json").open("a") as handle:
            handle.write(" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_pilot(self.root, run.name)

    def test_missing_explicit_run_has_rebuild_guidance(self):
        with self.assertRaisesRegex(ValueError, "Run prepare first"):
            resolve_runs(self.root, "missing-run")

    def test_unhashed_metadata_or_plotted_membership_rejected(self):
        run = self.pilot_run()
        manifest = json.loads((run / "manifest.json").read_text())
        original = dict(manifest["artifact_hashes"])
        for relative, message in (("normalization.json", "metadata must"),
                                  (str(Path("memberships/2015-01/membership-seed0.csv")), "plotted graph/membership")):
            with self.subTest(relative=relative):
                manifest["artifact_hashes"] = dict(original)
                del manifest["artifact_hashes"][relative]
                (run / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, message):
                    load_pilot(self.root, run.name)

    def test_unsafe_run_and_declared_artifact_paths_rejected(self):
        run = self.pilot_run()
        with self.assertRaisesRegex(ValueError, "inside project artifacts"):
            resolve_runs(self.root, "../../../outside")
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["artifact_hashes"]["../../../marker"] = "invalid"
        (run / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "unsafe artifact path"):
            verified_manifest(run, self.root / "artifacts")

    def test_source_manifest_replacement_rejected(self):
        run = self.pilot_run(separate=True)
        manifest = json.loads((run / "manifest.json").read_text())
        manifest["source_manifest_sha256"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "source manifest hash"):
            load_pilot(self.root, run.name)

    def test_resealed_reference_mismatch_rejected(self):
        run = self.pilot_run()
        data = json.loads((run / "detection.json").read_text())
        data["graph_reference"] = "other-reference"
        self.reseal(run, "detection.json", data)
        with self.assertRaisesRegex(ValueError, "graph_reference"):
            load_pilot(self.root, run.name)

    def test_resealed_identity_mismatch_rejected(self):
        run = self.pilot_run()
        data = json.loads((run / "normalization.json").read_text())
        data["identity_scope"] = "other-identities"
        self.reseal(run, "normalization.json", data)
        with self.assertRaisesRegex(ValueError, "identity scope"):
            load_pilot(self.root, run.name)

    def test_resealed_nonconserving_outcomes_rejected(self):
        run = self.pilot_run()
        data = json.loads((run / "snapshots.json").read_text())
        data["corpus_month_audit"][0]["reply_outcomes"]["valid"] += 1
        self.reseal(run, "snapshots.json", data)
        with self.assertRaisesRegex(ValueError, "conserve comments"):
            load_pilot(self.root, run.name)

    def test_resealed_duplicate_corpus_grid_rejected(self):
        run = self.pilot_run()
        data = json.loads((run / "snapshots.json").read_text())
        data["corpus_month_audit"][1] = data["corpus_month_audit"][0]
        self.reseal(run, "snapshots.json", data)
        with self.assertRaisesRegex(ValueError, "grid"):
            load_pilot(self.root, run.name)

    def test_deterministic_sample_and_empty_graph(self):
        run = self.pilot_run()
        pilot = load_pilot(self.root, run.name)
        first = sample_network(pilot, limit=2, seed=42)
        self.assertEqual(first, sample_network(pilot, limit=2, seed=42))
        self.assertEqual(len(first["nodes"]), 2)
        self.assertEqual(len(first["edges"]), 1)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            sample_network(pilot, limit=0)
        pilot["graphs"]["actual_months"] = ["2015-02"]
        self.assertEqual(sample_network(pilot)["nodes"], [])

    @unittest.skipUnless(HAS_PLOTS, "install [notebook]")
    def test_eight_figure_families_export_and_existing_output_protection(self):
        import matplotlib
        matplotlib.use("Agg")
        from reddit_sna.reporting.figures import build_figures, export_figures
        import matplotlib.pyplot as plt
        run = self.pilot_run()
        pilot = load_pilot(self.root, run.name)
        figures = build_figures(pilot, sample_limit=2)
        self.addCleanup(plt.close, "all")
        self.assertEqual(len(figures), 8)
        output = export_figures(figures, run.parent / "figures", pilot, sample_limit=2)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(len(manifest["artifact_hashes"]), 16)
        for relative, expected in manifest["artifact_hashes"].items():
            self.assertEqual(digest_file(output / relative), expected)
        self.assertEqual(manifest["source_manifest_sha256"]["detection"], digest_file(run / "manifest.json"))
        with self.assertRaises(FileExistsError):
            export_figures(figures, output, pilot)
        with self.assertRaisesRegex(ValueError, "inside project artifacts"):
            export_figures(figures, self.root / "data/figures", pilot)

    @unittest.skipUnless(HAS_PLOTS, "install [notebook]")
    def test_fully_empty_pilot_figures_preserve_missing_quality(self):
        from reddit_sna.reporting.figures import build_figures
        import matplotlib.pyplot as plt
        run = self.pilot_run(empty=True)
        pilot = load_pilot(self.root, run.name)
        figures = build_figures(pilot)
        self.addCleanup(plt.close, "all")
        self.assertEqual(len(figures), 8)
        self.assertTrue(all(d["runs"][0]["modularity"] is None for d in pilot["detection"]["months"]))
        self.assertTrue(all(g["reply_coverage_active_authors"] is None for g in pilot["graphs"]["months"]))
        self.assertEqual(corpus_matrix(pilot["graphs"])[2], [[0, 0, 0]])
        self.assertIn("Empty graph", figures["08_network_sample"].axes[0].texts[0].get_text())


class NotebookEnvironmentTests(unittest.TestCase):
    def test_missing_plotting_dependency_has_install_guidance(self):
        original_import = builtins.__import__
        def without_matplotlib(name, *args, **kwargs):
            if name.startswith("matplotlib"):
                raise ImportError("simulated unavailable optional dependency")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=without_matplotlib):
            with self.assertRaisesRegex(RuntimeError, "selected kernel.*Python"):
                plotting_dependencies()

    def test_wrong_kernel_preflight_reports_interpreter_and_setup(self):
        path = Path(__file__).parents[2] / "notebooks/core/01_reddit_pilot.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "".join(next(c for c in notebook["cells"] if c["id"] == "environment")["source"])
        original = importlib.util.find_spec
        with patch("importlib.util.find_spec", side_effect=lambda name: None if name == "reddit_sna" else original(name)):
            with self.assertRaises(RuntimeError) as failure:
                exec(source, {})
        self.assertIn(sys.executable, str(failure.exception))
        self.assertIn(".venv kernel", str(failure.exception))
        self.assertIn("pip install", str(failure.exception))
