"""Planted observability cases, not annotations or performance evidence."""

from copy import deepcopy
import unittest

from reddit_sna.evaluation.longitudinal import audit_rows, summarize
from reddit_sna.evaluation.temporal_protocol import FIELDS


def observations(months):
    return {m: dict(records=2, empty_corpora=[], authored={'a', 'b'}, posts={'a'},
        comments={'b'}, reply_endpoints=set()) for m in months}


class LongitudinalTests(unittest.TestCase):
    def setUp(self):
        # No edges exercises documented unit-importance fallback. Integration
        # fixtures below use actual graphs; this fixture isolates matching.
        self.data = {'2017-06': ({'c0': {'a', 'b'}}, []),
            '2017-07': ({'c1': {'x', 'y'}}, []),
            '2017-08': ({'c2': {'a', 'b'}}, []),
            '2017-09': ({'c3': {'a', 'b'}}, [])}
        self.obs = observations(self.data)
        self.labels = {('2017-06', 'c0'): dict(label='dissolve', reason='below_dissolve_threshold')}

    def rows(self, data=None, obs=None):
        return audit_rows(data or self.data, obs or self.obs, self.labels, 'fixture', '2018-01')

    def test_gap_later_candidate_preserves_original_label_and_clocks(self):
        before = deepcopy(self.labels)
        rows = [r for r in self.rows() if r['feature_month'] == '2017-06']
        self.assertEqual([r['accepted_matches'] for r in rows], [0, 1, 1])
        self.assertEqual([r['audit_observed_through_month'] for r in rows], ['2017-07', '2017-08', '2017-09'])
        self.assertTrue(all(r['feature_available_through_month'] == '2017-06' for r in rows))
        self.assertEqual(rows[0]['authored_fraction'], 1)
        self.assertEqual(rows[0]['partition_fraction'], 0)
        windows, strata = summarize(self.rows())
        self.assertEqual(windows[0]['window_status'], 'later_match_candidate')
        self.assertEqual(self.labels, before)
        self.assertEqual(sum(strata[0]['counts'].values()), len(windows))

    def test_missing_empty_partial_coverage_and_censored_are_not_negative_matches(self):
        for mode in ('missing', 'empty', 'partial'):
            data, obs = deepcopy(self.data), deepcopy(self.obs)
            if mode == 'missing':
                del data['2017-07']
            elif mode == 'empty':
                obs['2017-07']['records'] = 0
            else:
                obs['2017-07']['empty_corpora'] = ['fixture-corpus']
            windows, _ = summarize(self.rows(data, obs))
            self.assertEqual(windows[0]['window_status'], 'coverage_unknown')
        rows = audit_rows({'2017-12': ({'c0': {'a'}}, [])}, observations(['2017-12']), {}, 'fixture', '2018-01')
        self.assertTrue(all(r['right_censored'] and r['accepted_matches'] is None for r in rows))
        self.assertEqual(summarize(rows)[0][0]['window_status'], 'right_censored')
        self.assertEqual(summarize([]), ([], []))

    def test_future_perturbation_preserves_earlier_rows_and_not_features(self):
        before = self.rows()
        data, obs = deepcopy(self.data), deepcopy(self.obs)
        data['2017-09'] = ({'different': {'p', 'q'}}, [])
        obs['2017-09']['authored'] = {'p'}
        after = self.rows(data, obs)
        early = lambda rows: [r for r in rows if r['observation_month'] < '2017-09']
        self.assertEqual(early(before), early(after))
        self.assertFalse(set(before[0]) & {'authored_fraction', 'audit_observed_through_month'} & set(sum((list(v) for v in FIELDS.values()), [])))
        with self.assertRaises(ValueError):
            self.rows(dict(self.data, **{'2018-01': ({}, [])}))

    def test_weak_fragments_equal_size_changed_members_and_merge_ambiguity(self):
        data = {'2017-06': ({'a': {'1', '2'}, 'b': {'3', '4'}}, []),
            '2017-07': ({'x': {'1', '2', '3', '4'}}, [])}
        rows = audit_rows(data, observations(data), {}, 'fixture', '2018-01')
        self.assertTrue(all(r['accepted_merge_candidate'] for r in rows if r['horizon'] == 1 and r['feature_month'] == '2017-06'))
        data['2017-07'] = ({'x': {'1', '5'}, 'y': {'2', '6'}}, [])
        rows = audit_rows(data, observations(data), {}, 'fixture', '2018-01')
        first = rows[0]
        self.assertEqual(first['accepted_matches'], 0)
        self.assertEqual(first['max_inclusion_forward'], .25)
        self.assertEqual(first['strongest_shared_members'], 1)
        self.assertEqual(first['size_stratum'], 'le2')
        with self.assertRaises(ValueError):
            summarize([first, first])

    def test_complete_no_match_and_next_month_match_have_distinct_denominators(self):
        data = {m: ({'c0': {m+'a', m+'b'}}, []) for m in self.data}
        rows = self.rows(data)
        self.assertEqual(summarize(rows)[0][0]['window_status'], 'no_accepted_match_in_observed_window')
        data['2017-07'] = data['2017-06']
        self.assertEqual(summarize(self.rows(data))[0][0]['window_status'], 'accepted_next_month')
