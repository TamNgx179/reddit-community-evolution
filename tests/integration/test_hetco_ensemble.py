"""The pre-declared ensemble refuses uncommitted declarations and selects only on declared months."""

import csv
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from reddit_sna.evaluation.research import KEY
from reddit_sna.models.research import fit_variant, predict_variant
from reddit_sna.pipelines.hetco_ensemble import run_hetco_ensemble
from tests.integration.test_hetco import HeTCoPipelineTests, _write

DECLARATION = """schema_version = 1
protocol_id = "hetco-ensemble-test"
class_weight = "balanced"
head = "hierarchical"
poolings = ["attention", "mean"]
weights = [0.0, 0.5, 1.0]
partner = "B4_logreg"
control = "B5_matched_boosting"
seed_aggregation = "mean_probability"
selection_months = ["2015-03"]
selection_metric = "macro_f1_six"
tie_break = "lower_weight_then_attention"
"""


class HeTCoEnsembleTests(unittest.TestCase):
    def _fixture(self, root):
        preparation, research = HeTCoPipelineTests._fixture(None, root)
        protocol = json.loads((research / "protocol.json").read_text(encoding="utf-8"))
        with (research / "samples.csv").open(encoding="utf-8", newline="") as stream:
            samples = list(csv.DictReader(stream))
        predictions = []
        for window, boundary in (("main", "2015-04"), ("rolling", "2015-03"), ("rolling", "2015-04")):
            train = [r for r in samples if r["label_month"] < boundary]
            test = [r for r in samples if r["label_month"] == boundary]
            for name in ("B4_logreg", "B5_matched_boosting"):
                for seed in protocol["seeds"]:
                    predicted, _ = predict_variant(fit_variant(name, train, seed), test)
                    predictions += [{**{k: r[k] for k in KEY}, "window": window, "model": name, "seed": seed,
                                     "y_true": r["label"], "y_pred": str(p), "fallback": 0}
                                    for r, p in zip(test, predicted)]
        _write(research / "predictions.csv", predictions)
        declaration = root / "declaration.toml"
        declaration.write_text(DECLARATION, encoding="utf-8")
        for command in (["init", "-q"], ["add", "declaration.toml"],
                        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "declare"]):
            subprocess.run(["git", *command], cwd=root, check=True)
        return preparation, research, declaration

    def test_selects_on_declared_months_and_reports_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research, declaration = self._fixture(root)
            output = run_hetco_ensemble(declaration, research, preparation, root, "ensemble-test")
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "complete")
            self.assertIn(manifest["selected"]["weight"], (0.0, 0.5, 1.0))
            evaluation = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual({r["model"] for r in evaluation["comparison"]},
                             {"B4_logreg", "HeTCo_v2_seedavg", "HeTCo_v3", "Control_B4_B5"})
            with (output / "selection.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2 * 3 + 3)

    def test_refuses_uncommitted_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research, declaration = self._fixture(root)
            declaration.write_text(DECLARATION.replace("[0.0, 0.5, 1.0]", "[0.0, 1.0]"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Commit"):
                run_hetco_ensemble(declaration, research, preparation, root, "ensemble-dirty")


if __name__ == "__main__":
    unittest.main()
