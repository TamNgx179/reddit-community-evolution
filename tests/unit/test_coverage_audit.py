"""Coverage contract failures that would otherwise inflate reported coverage."""

import copy
import unittest

from reddit_sna.evaluation.coverage_audit import validate_coverage_inputs
from reddit_sna.evaluation.diagnostics import coverage_tables


def tables():
    features = [dict(reference_id='r', feature_month=m, community_id=c,
        available_through_month=m, size=size, history_missing=1)
        for m, c, size in [('2016-01', 'e', 8), ('2016-01', 'u', 2), ('2016-02', 't', 10)]]
    labels = [dict(reference_id='r', label_reference_id='l', feature_month='2016-01',
        label_month='2016-02', community_id=c, size=size, eligible=e, label=label, reason=reason)
        for c, size, e, label, reason in [('e', 8, '1', 'grow', 'one_to_one'),
                                         ('u', 2, '0', '', 'weak_overlap_unresolved')]]
    return features, labels


class CoverageAuditTests(unittest.TestCase):
    def test_known_denominators_and_explicit_missing_terminal(self):
        features, labels = tables()
        info = validate_coverage_inputs(features, labels, '2016-02')
        self.assertEqual(info['missing_terminal_targets'], 1)
        rows, _ = coverage_tables(labels, features)
        total = next(r for r in rows if r['axis'] == 'all')
        self.assertEqual((total['observed'], total['eligible'], total['unresolved'], total['censored']), (2, 1, 1, 1))
        self.assertEqual(total['coverage'], .5)
        self.assertEqual(total['member_month_coverage'], .8)

    def test_mixed_references_duplicates_and_wrong_month_rejected(self):
        features, labels = tables()
        mutations = [('reference_id', 'other'), ('label_reference_id', 'other'), ('label_month', '2016-03')]
        for field, value in mutations:
            with self.subTest(field=field):
                changed = copy.deepcopy(labels)
                changed[0][field] = value
                with self.assertRaises(ValueError):
                    validate_coverage_inputs(features, changed, '2016-02')
        with self.assertRaises(ValueError):
            validate_coverage_inputs(features, labels + labels[:1], '2016-02')

    def test_unresolved_must_not_be_relabelled_dissolve(self):
        features, labels = tables()
        labels[1]['label'] = 'dissolve'
        with self.assertRaises(ValueError):
            validate_coverage_inputs(features, labels, '2016-02')

    def test_censoring_cannot_hide_nonterminal_missing_or_bad_size(self):
        features, labels = tables()
        for changed in (labels[:1], [dict(labels[0], reason='final_snapshot_censored'), labels[1]],
                        [dict(labels[0], size=9), labels[1]]):
            with self.assertRaises(ValueError):
                validate_coverage_inputs(features, changed, '2016-02')
        with self.assertRaises(ValueError):
            validate_coverage_inputs(features, labels, '2016-01')

    def test_future_features_nonfinite_fractional_and_singleton_size_fail(self):
        features, labels = tables()
        for field, value in [('available_through_month', '2016-03'), ('size', float('nan')),
                             ('size', 2.5), ('size', 1), ('history_missing', .5)]:
            changed = copy.deepcopy(features)
            changed[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_coverage_inputs(changed, labels, '2016-02')

    def test_explicit_terminal_label_is_never_an_observed_event(self):
        features, labels = tables()
        labels.append(dict(reference_id='r', label_reference_id='l', feature_month='2016-02',
            community_id='t', label_month='2016-03', size=10, eligible='0', label='',
            reason='final_snapshot_censored'))
        validate_coverage_inputs(features, labels, '2016-02')
        labels[-1].update(eligible='1', label='dissolve')
        with self.assertRaises(ValueError):
            validate_coverage_inputs(features, labels, '2016-02')
