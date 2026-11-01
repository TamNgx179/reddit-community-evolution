"""The pre-declared v5 threshold run reuses research keys and pairs every fit with its argmax rule."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from reddit_sna.pipelines.hetco_threshold import load_declaration, run_hetco_threshold
from tests.integration.test_hetco import HeTCoPipelineTests

DECLARATION = """schema_version = 1
protocol_id = "test"
class_weight = "balanced"
head = "hierarchical"
members = "extended"
poolings = ["attention", "mean"]
control = "LR_hier_community"
thresholds = {thresholds}
selection_months = {months}
selection_metric = "macro_f1_six"
tie_break = "declaration_order"
placebo_stratum = "missing_no_shared"
"""
PROTOCOL = dict(test_start="2015-04", rolling_months=["2015-03", "2015-04"])


def _declare(root, thresholds='["argmax", 0.4, 0.6]', months='["2015-03"]'):
    path = root / "declaration.toml"
    path.write_text(DECLARATION.format(thresholds=thresholds, months=months), encoding="utf-8")
    return path


class HeTCoThresholdTests(unittest.TestCase):
    def test_declaration_rejects_late_months_and_missing_argmax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            load_declaration(_declare(root), PROTOCOL, require_commit=False)
            for kwargs in (dict(months='["2015-04"]'), dict(thresholds='[0.4, 0.6]'),
                           dict(thresholds='["argmax", 1.2]')):
                with self.assertRaises(ValueError):
                    load_declaration(_declare(root, **kwargs), PROTOCOL, require_commit=False)

    def test_uncommitted_declaration_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                load_declaration(_declare(Path(tmp)), PROTOCOL)

    def test_run_pairs_argmax_and_threshold_models_on_reference_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research = HeTCoPipelineTests._fixture(None, root)
            output = run_hetco_threshold(research, preparation, root, "v5-test", _declare(root),
                                         require_commit=False)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(set(manifest["selected"]), {"attention", "mean", "LR_hier_community"})
            with (output / "predictions.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            models = {"HeTCo_v4", "HeTCo_v5", "A7v4_mean_pool", "A7v5_mean_pool",
                      "LR_hier_community", "LR_hier_community_t1"}
            self.assertEqual({r["model"] for r in rows}, models)
            self.assertEqual(len(rows), len(models) * 2 * (4 + 8))
            with (output / "selection.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 3 * 3)
            # Each pair comes from one fit, so probabilities agree row by row.
            by_key = {}
            for r in rows:
                by_key.setdefault((r["window"], r["seed"], r["community_id"], r["feature_month"],
                                   r["model"].replace("v5", "v4").removesuffix("_t1")), set()).add(r["p_dissolve"])
            self.assertTrue(all(len(v) == 1 for v in by_key.values()))
            with self.assertRaises(ValueError):
                run_hetco_threshold(research, preparation, root, "v5-test", _declare(root), require_commit=False)


if __name__ == "__main__":
    unittest.main()
