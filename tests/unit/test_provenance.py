import csv
import json

from reddit_sna.graphs.provenance import EDGE_COLUMNS, snapshot_inventory
from reddit_sna.graphs.snapshots import write_csv
from tests.corpus_support import CorpusCase


class ProvenanceTests(CorpusCase):
    def graph(self, month="2015-01", rows=None):
        directory = self.root / "graphs" / month
        directory.mkdir(parents=True, exist_ok=True)
        write_csv(directory / "R.csv", EDGE_COLUMNS,
                  rows if rows is not None else [(month, "u1", "u2", 1)])
        return directory.parent

    def test_changed_content_or_protocol_changes_cohort_reference(self):
        source = self.graph()
        first = snapshot_inventory(source)
        second = snapshot_inventory(source, protocol="alternative-projection-v1")
        self.assertNotEqual(first["graph_reference"], second["graph_reference"])
        self.assertEqual(first["month_graphs"], second["month_graphs"])
        (source / "2015-01/R.csv").write_text("month,source_user_id,target_user_id,weight\n2015-01,u1,u2,9\n")
        third = snapshot_inventory(source)
        self.assertNotEqual(first["graph_reference"], third["graph_reference"])
        self.assertNotEqual(first["month_graphs"], third["month_graphs"])

    def test_adding_month_changes_cohort_but_preserves_past_digest(self):
        source = self.graph()
        first = snapshot_inventory(source)
        self.graph("2015-02", [])
        second = snapshot_inventory(source)
        self.assertEqual(first["month_graphs"][0], second["month_graphs"][0])
        self.assertNotEqual(first["graph_reference"], second["graph_reference"])
        self.assertEqual(second["end_month_exclusive"], "2015-03")
        with self.assertRaisesRegex(ValueError, "metadata months"):
            snapshot_inventory(source, expected_months=["2015-01"])

    def test_gap_empty_and_mislabeled_month_are_rejected(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, "at least one"):
            snapshot_inventory(empty)
        source = self.graph(rows=[("2015-02", "u1", "u2", 1)])
        with self.assertRaisesRegex(ValueError, "edge month"):
            snapshot_inventory(source)
        self.graph("2015-03", [])
        with self.assertRaisesRegex(ValueError, "consecutive"):
            snapshot_inventory(source)

    def test_reverse_duplicates_and_nonfinite_weights_are_rejected(self):
        source = self.graph()
        for rows in ([('2015-01','u1','u2',1),('2015-01','u2','u1',1)],
                     [('2015-01','u1','u2','nan')]):
            with self.subTest(rows=rows):
                with (source/'2015-01/R.csv').open('w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(EDGE_COLUMNS)
                    writer.writerows(rows)
                with self.assertRaisesRegex(ValueError, "unique non-self"):
                    snapshot_inventory(source)
