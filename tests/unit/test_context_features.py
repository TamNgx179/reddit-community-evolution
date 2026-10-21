"""Hand-calculated context and future-perturbation tests using real SQLite."""

import math
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from reddit_sna.data.normalize import month_boundary
from reddit_sna.features.context import context_features
from reddit_sna.features.lagged import predecessor_features


class ContextFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'data.sqlite'
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('CREATE TABLE records(user_id TEXT,root TEXT,corpus TEXT,timestamp REAL,month TEXT)')
            db.executemany('INSERT INTO records VALUES(?,?,?,?,?)', [
                ('a', 'thread', 'Conservative', month_boundary('2015-01'), '2015-01'),
                ('b', 'thread', 'socialism', month_boundary('2015-01'), '2015-01'),
                ('z', 'thread', 'socialism', month_boundary('2015-01'), '2015-01'),
                ('a', 'solo', 'socialism', month_boundary('2015-01'), '2015-01'),
                (None, 'invalid', 'socialism', month_boundary('2015-01'), '2015-01')])
        self.groups = {'A': {'a', 'b'}, 'B': {'c'}}

    def test_exact_entropy_exposure_activity_and_missing_observation(self):
        result = context_features(self.db, '2015-01', self.groups)
        entropy = -(math.log(1/3)/3 + 2*math.log(2/3)/3) / math.log(15)
        self.assertAlmostEqual(result['A']['subreddit_entropy'], entropy)
        self.assertAlmostEqual(result['A']['thread_activity'], math.log(2))
        self.assertEqual(result['A']['active_member_fraction'], 1)
        self.assertEqual(result['A']['co_thread_external_exposure'], .5)
        self.assertEqual(set(result['B'].values()), {0})

    def test_future_thread_participants_cannot_change_past_context(self):
        before = context_features(self.db, '2015-01', self.groups)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executemany('INSERT INTO records VALUES(?,?,?,?,?)', [
                (f'future-{i}', 'thread', 'socialism', month_boundary('2015-02'), '2015-02')
                for i in range(40)])
            db.execute("UPDATE records SET corpus='Conservative' WHERE month='2015-02'")
        self.assertEqual(context_features(self.db, '2015-01', self.groups), before)

    def test_empty_month_and_singleton_thread_are_finite(self):
        self.assertTrue(all(v == 0 for r in context_features(self.db, '2014-12', self.groups).values() for v in r.values()))
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("DELETE FROM records WHERE root='thread'")
        result = context_features(self.db, '2015-01', self.groups)
        self.assertEqual(result['A']['co_thread_external_exposure'], 0)
        self.assertEqual(result['A']['active_member_fraction'], .5)

    def test_inconsistent_timestamp_and_duplicate_membership_refused(self):
        with self.assertRaisesRegex(ValueError, 'assigned twice'):
            context_features(self.db, '2015-01', {'A': {'a'}, 'B': {'a'}})
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE records SET timestamp=? WHERE user_id='a'", (month_boundary('2015-02'),))
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            context_features(self.db, '2015-01', self.groups)

    def test_predecessor_lags_and_persistence_ignore_outgoing_future_labels(self):
        features = {('2015-01','old'): dict(size=2,density=1,internal_weight=3),
                    ('2015-02','new'): dict(size=3,density=.5,internal_weight=4)}
        labels = [dict(feature_month='2015-01',community_id='old',eligible='1',label='grow'),
                  dict(feature_month='2015-02',community_id='new',eligible='1',label='split')]
        links = [dict(feature_month='2015-01',label_month='2015-02',community_id='old',target_community_id='new',match_score='1')]
        result = predecessor_features(['2015-01','2015-02'],features,labels,links)
        self.assertEqual(result[('2015-02','new')],
                         (dict(lag_size=2,lag_density=1,lag_internal_weight=3,lag_missing=0),'grow'))
        self.assertEqual(result[('2015-01','old')][0]['lag_missing'],1)
        labels[1]['label']='dissolve'
        self.assertEqual(predecessor_features(['2015-01','2015-02'],features,labels,links),result)

    def test_lag_requires_immediately_previous_source(self):
        with self.assertRaisesRegex(ValueError, 'immediately previous'):
            predecessor_features(['2015-01','2015-02'],{('2015-02','new'):{}},[],[
                dict(feature_month='2014-12',label_month='2015-02',community_id='old',target_community_id='new',match_score='1')])
