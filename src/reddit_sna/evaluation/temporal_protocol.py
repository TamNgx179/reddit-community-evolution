"""Frozen full-study schedule and bounded, equally budgeted model families."""

from itertools import product
import json
from pathlib import Path
import tomllib

from reddit_sna.contracts import Event, next_month
from reddit_sna.evaluation.research_protocol import FULL
from reddit_sna.features.activity import ACTIVITY_FIELDS, DYNAMIC_FIELDS

EVENTS = tuple(e.value for e in Event)
FIELDS = {"static": FULL + ACTIVITY_FIELDS,
          "dynamic": FULL + ACTIVITY_FIELDS + DYNAMIC_FIELDS}
COUNT_FIELDS = frozenset(('size','internal_edges','internal_weight','boundary_weight',
    'community_age','predecessor_count','lag_size','lag_internal_weight'))
# Roles are fixed, not sorted or selected from final-period scores. In the
# historical full run these retain its preselected primary and strongest control.
COMPACT_MODELS = ('B1_majority','B1_persistence','flat_lr_dynamic','hier_hgb_static',
                  'hier_hgb_dynamic','hier_lr_dynamic','A_no_dynamics_matched')
COMPACT_BASELINES = COMPACT_MODELS[:5]
PRIMARY = 'hier_lr_dynamic'
LR_SETTINGS = tuple(dict(estimator="lr", C=c, class_weight=w, transform=t)
                    for c, w, t in product((.1, 1.), (None, "balanced"), ("standard", "log_counts")))
HGB_SETTINGS = tuple(dict(estimator="hgb", max_leaf_nodes=l, min_samples_leaf=n, class_weight=w)
                     for l, n, w in product((7, 15), (5, 20), (None, "balanced")))
SETTINGS = dict(lr=LR_SETTINGS, hgb=HGB_SETTINGS)


def months(start, end):
    """List a nonempty half-open monthly interval without day approximations."""
    next_month(start)
    next_month(end)
    if start >= end:
        raise ValueError("Nonempty month interval required")
    result = []
    while start < end:
        result.append(start)
        start = next_month(start)
    return result


def load_temporal_protocol(path):
    """Reject undeclared schedules/search budgets instead of silently retuning."""
    actual = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    expected = dict(schema_version=3, protocol_id="activity-interaction-five-baselines-v3",
        start="2015-01", validation_start="2017-07", test_start="2018-01", end="2018-10",
        seeds=[42,43,44], selection_seed=42, bootstrap_draws=2000, block_length=3,
        bootstrap_seed=2026, working_budget_gib=30, memory_budget_gib=8, minimum_free_gib=12,
        exposure="chronological_development_unseen_uncertified")
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("Unsupported temporal study protocol")
    return actual


def resolved_protocol(protocol):
    return dict(**protocol, fields={k:list(v) for k,v in FIELDS.items()},
        candidates=SETTINGS, labels=EVENTS, count_fields=sorted(COUNT_FIELDS),
        models=list(COMPACT_MODELS),primary=PRIMARY,
        graph="reply-r-v3-order1; weighted Leiden RB gamma1 canonical seed0",
        tracker="ged-strength-topology-v1 alpha=.5 beta=.5 dissolve=.1",
        selection="pooled fixed-six-class Macro-F1; first-declared ties",
        test_model="frozen fit through December2017; no test-label refitting",
        human_review="pending", novelty="unverified", unseen=False)
