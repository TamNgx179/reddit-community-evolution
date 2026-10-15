import csv

from reddit_sna.data.normalize import normalize_archives
from reddit_sna.graphs.snapshots import build_snapshots
from tests.corpus_support import CorpusCase, record


class SnapshotTests(CorpusCase):
    def test_appending_future_records_does_not_change_earlier_graphs(self):
        rows = [record("p", day="2014-12-31"), record("a", "synthetic_B", parent="p")]
        first, second = self.root / "first.sqlite", self.root / "second.sqlite"
        normalize_archives([self.raw(rows)], first, "2015-04", self.quiet)
        normalize_archives([self.raw(rows + [record("future", "future_user", parent="p", day="2015-04-01")])], second, "2015-04", self.quiet)
        build_snapshots(first, self.root / "g1", "2015-01", "2015-04")
        build_snapshots(second, self.root / "g2", "2015-01", "2015-04")
        for month in ("2015-01", "2015-02", "2015-03"):
            for filename in ("R.csv", "directed_R.csv", "users.csv"):
                self.assertEqual((self.root / "g1" / month / filename).read_bytes(),
                                 (self.root / "g2" / month / filename).read_bytes())

    def test_weight_loss_coverage_and_empty_month(self):
        rows = [record("p", day="2014-12-31"),
                record("a", "synthetic_B", parent="p"),
                record("b", "synthetic_B", parent="p"),
                record("c", "synthetic_A", parent="a"),
                record("self", "synthetic_A", parent="p"),
                record("miss", "synthetic_C", parent="missing"),
                record("bot", "AutoModerator", parent="p"),
                record("later", "synthetic_B", parent="future"),
                record("future", "synthetic_C", parent="p", day="2015-02-01")]
        database = self.root / "normalized.sqlite"
        normalize_archives([self.raw(rows)], database, "2015-04", self.quiet)
        result = build_snapshots(database, self.root / "graphs", "2015-01", "2015-04")
        jan, feb, march = result["months"]
        self.assertEqual(jan["reply_events"], 3)
        self.assertEqual(jan["undirected_edges"], 1)
        self.assertEqual(jan["missing_parent"], 1)
        self.assertEqual(jan["parent_after_child"], 1)
        self.assertEqual(jan["self_reply_incidence"], 1)
        self.assertEqual(jan["isolates"], 1)
        self.assertEqual(march["reply_coverage_observed_users"], None)
        self.assertEqual(feb["parent_only_endpoints"], 1)
        with (self.root / "graphs/2015-01/R.csv").open() as handle:
            edge = list(csv.DictReader(handle))[0]
        self.assertEqual(edge["weight"], "3")

    def test_snapshot_cannot_exceed_normalization_cutoff(self):
        database = self.root / "normalized.sqlite"
        normalize_archives([self.raw()], database, "2015-04", self.quiet)
        with self.assertRaisesRegex(ValueError, "cutoff"):
            build_snapshots(database, self.root / "graphs", "2015-01", "2015-05")
