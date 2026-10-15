import csv
from contextlib import closing
import importlib.util
import sqlite3
import unittest

from reddit_sna.data.normalize import normalize_archives
from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.evaluation.causality import compare_causal_prefix
from reddit_sna.graphs.snapshots import build_snapshots
from reddit_sna.graphs.snapshots import write_csv
from tests.corpus_support import CorpusCase, record


@unittest.skipUnless(importlib.util.find_spec('leidenalg'), 'install [graph] for partition causality checks')
class CausalityTests(CorpusCase):
    def setUp(self):
        super().setUp()
        old = [record('p'), record('c','synthetic_B',parent='p'),
               record('q','synthetic_C',root='q'), record('early','synthetic_E',parent='t3_later')]
        future = [record('future','synthetic_B',parent='p',day='2015-02-01'), *old,
                  record('later','synthetic_D',root='later',day='2015-03-01')]
        self.maps = []
        for name, rows in (('a',old),('b',future)):
            directory = self.root/name
            directory.mkdir()
            dbpath = directory/'normalized.sqlite'
            normalize_archives([self.raw(rows)],dbpath,'2015-04',self.quiet)
            build_snapshots(dbpath,directory/'graphs','2015-01','2015-04',corpora=('moderatepolitics',))
            detect_snapshots(directory/'graphs',directory/'memberships',name,seeds=(0,))
            known = {'t3_p':'A','t1_c':'B','t3_q':'C','t1_early':'E'}
            with closing(sqlite3.connect(dbpath)) as db:
                self.maps.append({uid:known[rid] for rid,uid in db.execute('SELECT id,user_id FROM records WHERE month=?',('2015-01',))})

    def compare(self, **kwargs):
        return compare_causal_prefix(self.root/'a/graphs',self.root/'b/graphs','2015-01',
               left_user_map=self.maps[0],right_user_map=self.maps[1],
               left_memberships=self.root/'a/memberships',right_memberships=self.root/'b/memberships',**kwargs)

    def rewrite(self, path, transform):
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            columns, rows = reader.fieldnames,list(reader)
        with path.open('w',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=columns)
            writer.writeheader()
            writer.writerows(transform(rows))

    def test_within_pilot_future_append_identity_alignment_and_label_permutation(self):
        self.assertNotEqual(self.maps[0], self.maps[1])
        membership = self.root/'b/memberships/2015-01/membership-seed0.csv'
        self.rewrite(membership,lambda rows:[dict(r,community_id='renamed-'+r['community_id']) for r in rows])
        # Invalid future CSVs are deliberately not opened by the past diagnostic.
        (self.root/'b/graphs/2015-02/R.csv').write_text('NOT A VALID GRAPH')
        result = self.compare()
        self.assertTrue(result['graph_invariant'])
        self.assertTrue(result['partition_invariant'])
        self.assertEqual(len(result['months']),1)

    def test_changed_past_edge_is_detected(self):
        path = self.root/'b/graphs/2015-01/R.csv'
        self.rewrite(path,lambda rows:[dict(r,weight='99') for r in rows])
        self.assertFalse(self.compare()['graph_invariant'])

    def test_changed_partition_is_detected_without_relying_on_cluster_names(self):
        path = self.root/'b/memberships/2015-01/membership-seed0.csv'
        self.rewrite(path,lambda rows:[dict(r,community_id=f'split{i}') for i,r in enumerate(rows)])
        result = self.compare()
        self.assertTrue(result['graph_invariant'])
        self.assertFalse(result['partition_invariant'])

    def test_incomplete_alignment_or_membership_is_not_a_false_pass(self):
        self.maps[1] = {}
        with self.assertRaisesRegex(ValueError,'identity alignment'):
            self.compare()

    def test_missing_membership_endpoint_is_rejected(self):
        path = self.root/'b/memberships/2015-01/membership-seed0.csv'
        self.rewrite(path,lambda rows:rows[:1])
        with self.assertRaisesRegex(ValueError,'graph endpoints'):
            self.compare()

    def test_edgeless_partition_and_isolate_are_compared_without_quality_claims(self):
        for name in ('empty_a','empty_b'):
            directory = self.root/name/'2015-01'
            directory.mkdir(parents=True)
            for filename in ('R.csv','directed_R.csv'):
                write_csv(directory/filename,['month','source_user_id','target_user_id','weight'],[])
            write_csv(directory/'users.csv',['user_id','authored_in_month','has_reply_edge'],[('u0',1,0)])
            write_csv(directory/'membership-seed0.csv',['reference_id','month','community_id','user_id'],[])
        result = compare_causal_prefix(self.root/'empty_a',self.root/'empty_b','2015-01',
                  left_user_map={'u0':'only'},right_user_map={'u0':'only'},
                  left_memberships=self.root/'empty_a',right_memberships=self.root/'empty_b')
        self.assertTrue(result['graph_invariant'])
        self.assertTrue(result['partition_invariant'])

    def test_many_to_one_alignment_is_rejected(self):
        self.maps[1] = dict.fromkeys(self.maps[1], 'collapsed')
        with self.assertRaisesRegex(ValueError,'one-to-one'):
            self.compare()
