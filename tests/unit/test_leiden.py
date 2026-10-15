import importlib.util
import itertools
import unittest

from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.graphs.snapshots import write_csv
from tests.corpus_support import CorpusCase


@unittest.skipUnless(importlib.util.find_spec("leidenalg"), "install [graph] for Leiden tests")
class LeidenTests(CorpusCase):
    def test_membership_reference_binds_graph_content_and_is_shared_across_months(self):
        source = self.root/'graphs'
        for month in ('2015-01','2015-02'):
            (source/month).mkdir(parents=True)
            write_csv(source/month/'R.csv', ['month','source_user_id','target_user_id','weight'],
                      [(month,'u1','u2',1)])
        a = detect_snapshots(source,self.root/'first','identity',seeds=(0,))
        refs_a = {m['runs'][0]['reference_id'] for m in a['months']}
        self.assertEqual(len(refs_a),1)
        (source/'2015-01/R.csv').write_text('month,source_user_id,target_user_id,weight\n2015-01,u1,u2,9\n')
        b = detect_snapshots(source,self.root/'second','identity',seeds=(0,))
        self.assertNotEqual(refs_a,{m['runs'][0]['reference_id'] for m in b['months']})
        self.assertEqual(a['month_graphs'][1],b['month_graphs'][1])

    def test_known_disconnected_cliques_and_empty_graph(self):
        source = self.root / "graphs"
        (source / "2015-01").mkdir(parents=True)
        (source / "2015-02").mkdir()
        columns = ["month", "source_user_id", "target_user_id", "weight"]
        edges = [("2015-01", f"u{a}", f"u{b}", 1)
                 for block in (range(4), range(4, 8)) for a, b in itertools.combinations(block, 2)]
        write_csv(source / "2015-01/R.csv", columns, edges)
        write_csv(source / "2015-02/R.csv", columns, [])
        result = detect_snapshots(source, self.root / "memberships", "synthetic")
        for run in result["months"][0]["runs"]:
            self.assertEqual(run["communities"], 2)
            self.assertEqual(run["sizes"], [4, 4])
            self.assertTrue(run["all_communities_connected"])
        self.assertEqual(result["months"][0]["seed_pair_ARI"], [1.0, 1.0, 1.0])
        self.assertEqual(result["months"][1]["runs"][0]["status"], "empty_graph_no_partition")

    def test_invalid_edge_is_rejected(self):
        month = self.root / "graphs/2015-01"
        month.mkdir(parents=True)
        write_csv(month / "R.csv", ["month", "source_user_id", "target_user_id", "weight"],
                  [("2015-01", "u1", "u1", 1)])
        with self.assertRaisesRegex(ValueError, "unique non-self"):
            detect_snapshots(month.parent, self.root / "out", "synthetic")
