import unittest

from reddit_sna.evaluation.constrained_blend import (
    HGB, LR, blend, development_predictions, match_predictions, select_weight,
)
from reddit_sna.evaluation.temporal_protocol import EVENTS, SETTINGS


def row(number, truth, **distribution):
    probabilities = [distribution.get(event, 0.0) for event in EVENTS]
    return dict(reference_id="graph", feature_month="2017-06", community_id=str(number),
                label_month="2017-07", label_reference_id="labels", seed=42,
                y_true=truth, y_pred=max(distribution, key=distribution.get),
                probabilities=probabilities, fallback=0)


class ConstrainedBlendTests(unittest.TestCase):
    def test_development_cutoff(self):
        definitions = {
            model: dict(fields=["size"], settings=SETTINGS[estimator][0], hierarchical=True)
            for model, estimator in ((LR, "lr"), (HGB, "hgb"))
        }
        samples = [
            dict(row(1, "dissolve", dissolve=1), label="dissolve", label_month="2017-06", size=2),
            dict(row(2, "grow", grow=1), label="grow", size=3),
        ]
        protocol = dict(validation_start="2017-07", test_start="2018-01", seeds=[42])
        pairs, fit_log = development_predictions(samples, definitions, protocol)
        self.assertEqual(len(pairs), 1)
        self.assertEqual({r["latest_train_label"] for r in fit_log}, {"2017-06"})
        self.assertEqual({r["validation_month"] for r in fit_log}, {"2017-07"})
        with self.assertRaisesRegex(ValueError, "final-window"):
            development_predictions(samples + [dict(samples[1], label_month="2018-01")],
                                    definitions, protocol)

    def test_reject_invalid_matched_rows(self):
        lr = row(1, "grow", grow=1)
        for right in (
            [lr, lr],
            [dict(lr, community_id="other")],
            [dict(lr, community_id="")],
            [dict(lr, y_true="merge")],
            [dict(lr, probabilities=[float("nan")] * len(EVENTS))],
            [dict(lr, probabilities=[0] * len(EVENTS))],
            [dict(lr, y_pred="split")],
        ):
            with self.subTest(right=right), self.assertRaises(ValueError):
                match_predictions([lr], right)

    def test_missing_support_retains_identity(self):
        r = row(1, "grow", grow=1)
        pairs = match_predictions([r], [r])
        self.assertEqual(select_weight(pairs, [42])["reason"], "missing_rare_class_support")
        self.assertEqual(blend(pairs, 0)[0]["y_pred"], r["y_pred"])

    def test_ties_retain_identity_and_eligible_blend_improves(self):
        lr = [row(1, "grow", grow=.6, dissolve=.4), row(2, "merge", merge=.45, dissolve=.55)]
        hgb = [row(1, "grow", grow=.45, dissolve=.55), row(2, "merge", merge=.6, dissolve=.4)]
        no_gain = select_weight(match_predictions(lr, lr), [42])
        self.assertEqual((no_gain["weight"], no_gain["reason"]),
                         (0.0, "no_blend_passed_development_constraints"))
        decision = select_weight(match_predictions(lr, hgb), [42])
        self.assertEqual(decision["weight"], .5)
        self.assertEqual(decision["reason"], "eligible_blend_selected")


if __name__ == "__main__":
    unittest.main()
