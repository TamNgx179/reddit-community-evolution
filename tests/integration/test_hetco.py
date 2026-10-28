"""The HeTCo command reuses a research run's exact keys and writes verifiable outputs."""

import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from reddit_sna.contracts import next_month
from reddit_sna.evaluation.research import KEY
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.pipelines.hetco import MODELS, REFERENCES, community_delta, run_hetco
from reddit_sna.reporting.hetco import export_figures, read_hetco

MONTHS = ["2015-01", "2015-02", "2015-03"]
EVENTS = ["grow", "stable", "shrink", "dissolve"]


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class HeTCoPipelineTests(unittest.TestCase):
    def _fixture(self, root):
        preparation, research = root / "core/prep", root / "research/run"
        (preparation / "snapshots").mkdir(parents=True)
        (preparation / "manifest.json").write_text("{}", encoding="utf-8")
        (preparation / "detection.json").write_text(json.dumps({"canonical_seed": 0}), encoding="utf-8")
        db = sqlite3.connect(preparation / "normalized.sqlite")
        db.execute("CREATE TABLE records(id TEXT PRIMARY KEY, user_id TEXT, root TEXT, parent TEXT,"
                   " timestamp REAL, month TEXT, kind TEXT, corpus TEXT)")
        db.execute("CREATE TABLE provenance(key TEXT PRIMARY KEY, value TEXT)")
        samples, record = [], 0
        for m_index, month in enumerate(MONTHS):
            members, edges = [], []
            for c in range(4):
                users = [f"u{c}{k}" for k in range(2 + c)]
                members += [dict(reference_id="ref", month=month, community_id=f"c{c}", user_id=u) for u in users]
                edges += [dict(month=month, source_user_id=a, target_user_id=b, weight=c + 1)
                          for a, b in zip(users, users[1:])]
                for u in users:
                    record += 1
                    db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?)",
                               (str(record), u, "r", None, 0, month, "comment", "X"))
                samples.append(dict(reference_id="ref", feature_month=month, community_id=f"c{c}",
                                    label_month=next_month(month), label_reference_id="labels",
                                    label=EVENTS[(c + m_index) % 4], past_event="",
                                    **{f: (c + 1) * (i + 1) / 10 for i, f in enumerate(FULL)}))
            _write(preparation / f"memberships/{month}/membership-seed0.csv", members)
            _write(preparation / f"snapshots/{month}/R.csv", edges)
        db.commit()
        db.close()
        protocol = dict(test_start="2015-04", rolling_months=["2015-03", "2015-04"], seeds=[42, 43],
                        bootstrap=dict(block_length=1, draws=20, seed=2026, minimum_months=2))
        research.mkdir(parents=True)
        (research / "manifest.json").write_text(json.dumps(dict(
            status="complete", source_preparation=str(preparation.resolve()))), encoding="utf-8")
        (research / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
        _write(research / "samples.csv", samples)
        predictions = []
        for window, selected in (("main", ["2015-04"]), ("rolling", ["2015-03", "2015-04"])):
            for model in REFERENCES:
                for seed in protocol["seeds"]:
                    predictions += [{**{k: r[k] for k in KEY}, "window": window, "model": model, "seed": seed,
                                     "y_true": r["label"], "y_pred": "grow", "fallback": 0}
                                    for r in samples if r["label_month"] in selected]
        _write(research / "predictions.csv", predictions)
        return preparation, research

    def test_run_matches_reference_keys_and_exports_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research = self._fixture(root)
            output = run_hetco(research, preparation, root, "hetco-test")
            delivery = read_hetco(output)
            models = {r["model"] for r in delivery["evaluation"]["comparison"]}
            self.assertEqual(models, {*REFERENCES, *MODELS})
            with (output / "predictions.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(MODELS) * 2 * (4 + 8))
            self.assertEqual(len(delivery["attention"]), 4)
            manifest = delivery["manifest"]
            self.assertEqual(manifest["models"]["HeTCo_v2"]["head"], manifest["selected"]["head"])
            with (output / "selection.csv").open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 6)
            self.assertTrue((export_figures(output, root / "figures") / "attention.png").exists())
            with self.assertRaises(ValueError):
                run_hetco(research, preparation, root, "hetco-test")

    def test_community_bootstrap_is_paired(self):
        rows = [dict(reference_id="r", feature_month="2015-03", community_id=f"c{i}", label_month="2015-04",
                     label_reference_id="l", y_true="grow" if i % 2 else "dissolve", y_pred="grow")
                for i in range(10)]
        units = {("main", m, s): rows for m in ("a", "b") for s in (1, 2)}
        same = community_delta(units, "a", "b", [1, 2], draws=50)
        self.assertEqual((same["observed"], same["low"], same["high"]), (0.0, 0.0, 0.0))
        better = [{**r, "y_pred": r["y_true"]} for r in rows]
        units.update({("main", "a", s): better for s in (1, 2)})
        self.assertGreater(community_delta(units, "a", "b", [1, 2], draws=50)["low"], 0)

    def test_model_subset_without_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research = self._fixture(root)
            output = run_hetco(research, preparation, root, "hetco-subset", ["HeTCo_v1"])
            self.assertFalse((output / "selection.csv").exists())
            self.assertEqual({r["model"] for r in read_hetco(output)["evaluation"]["comparison"]},
                             {*REFERENCES, "HeTCo_v1"})

    def test_refuses_research_run_from_another_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preparation, research = self._fixture(root)
            other = root / "core/other"
            other.mkdir()
            with self.assertRaises(ValueError):
                run_hetco(research, other, root, "hetco-other")


if __name__ == "__main__":
    unittest.main()
