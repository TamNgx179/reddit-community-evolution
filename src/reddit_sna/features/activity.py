"""Cutoff-safe activity and fixed-membership interaction dynamics.

All historical aggregates use the current community's members. No predecessor
choice, future membership, completed thread or target label enters this API.
"""

import calendar
from collections import Counter, defaultdict
from contextlib import closing
import math

from reddit_sna.contracts import next_month, shift_month
from reddit_sna.data.normalize import month_boundary, open_readonly
from reddit_sna.graphs.audit import VALID_REPLY

ACTIVITY_FIELDS = ("records_per_member_log", "active_day_fraction", "recent_record_fraction",
                   "top_member_fraction", "internal_reply_fraction", "weighted_reciprocity",
                   "activity_missing", "reply_missing")
DYNAMIC_FIELDS = ("returning_member_fraction", "past_active_month_fraction", "record_log_growth",
                  "reply_log_growth", "repeated_dyad_fraction", "context_drift_js",
                  "past_window_fraction", "context_history_missing", "previous_reply_missing")


def _js(left, right):
    """Natural-log Jensen-Shannon divergence; both inputs must have positive mass."""
    a, b = sum(left.values()), sum(right.values())
    if not a or not b:
        return 0.0
    result = 0.0
    # Identical historical features must serialize identically across worker
    # hash seeds; set traversal otherwise changes low-order floating bits.
    for key in sorted(left.keys() | right.keys()):
        p, q = left[key] / a, right[key] / b
        mid = (p + q) / 2
        if p:
            result += .5 * p * math.log(p / mid)
        if q:
            result += .5 * q * math.log(q / mid)
    return result


def activity_features(database, month, groups):
    """Return finite A/D fields with explicit empty-denominator/history flags.

    Historical coverage counts months with any observed corpus records; it is
    not proof that each account/corpus was comprehensively observed. Record
    identifiers are not returned. Reply validity matches the primary graph.
    """
    owners = {}
    for cid, users in groups.items():
        if not cid or not users or owners.keys() & users:
            raise ValueError("Activity groups must be nonempty and disjoint")
        owners.update(dict.fromkeys(users, cid))
    start, end = month_boundary(month), month_boundary(next_month(month))
    previous = shift_month(month, -1)
    lower = shift_month(month, -3)
    counts, corpora = defaultdict(Counter), defaultdict(Counter)
    days, recent, prior_active = defaultdict(set), Counter(), defaultdict(set)
    internal, authored_replies = defaultdict(Counter), Counter()
    days_in_month = calendar.monthrange(*map(int, month.split("-")))[1]
    with closing(open_readonly(database)) as db:
        cutoff = dict(db.execute("SELECT key,value FROM provenance")).get("end_month_exclusive")
        if cutoff is None or next_month(month) > cutoff:
            raise ValueError("Activity month exceeds normalized observation cutoff")
        # GROUP BY compresses record traffic; the day is a UTC epoch day.
        for m, user, corpus, day, n in db.execute("""SELECT month,user_id,corpus,
                CAST(timestamp/86400 AS INTEGER),COUNT(*) FROM records
                WHERE month>=? AND month<=? AND timestamp>=? AND timestamp<?
                AND user_id IS NOT NULL GROUP BY month,user_id,corpus,4""",
                (lower, month, month_boundary(lower), end)):
            if user not in owners:
                continue
            cid = owners[user]
            counts[(m, cid)][user] += n
            corpora[(m, cid)][corpus] += n
            if m == month:
                days[cid].add(day)
                recent[cid] += n if day * 86400 >= end - 7 * 86400 else 0
            else:
                prior_active[cid].add((m, user))
        observed = {r[0] for r in db.execute("SELECT DISTINCT month FROM records WHERE month>=? AND month<? AND timestamp<?",
                                           (lower, month, start))}
        for m in (previous, month):
            for u, v, weight in db.execute(f"""SELECT c.user_id,p.user_id,COUNT(*)
                    FROM records c JOIN records p ON c.parent=p.id
                    WHERE c.month=? AND c.timestamp>=? AND c.timestamp<?
                    AND c.kind='comment' AND {VALID_REPLY}
                    GROUP BY c.user_id,p.user_id""",
                    (m, month_boundary(m), month_boundary(next_month(m)))):
                cid = owners.get(u)
                if cid is None:
                    continue
                if m == month:
                    authored_replies[cid] += weight
                if owners.get(v) == cid:
                    internal[(m, cid)][(u, v)] += weight
    result = {}
    for cid, users in groups.items():
        now, past = counts[(month, cid)], counts[(previous, cid)]
        n, before = sum(now.values()), sum(past.values())
        directed, old = internal[(month, cid)], internal[(previous, cid)]
        weight, old_weight = sum(directed.values()), sum(old.values())
        old_pairs = {frozenset(pair) for pair in old}
        reciprocal = sum(min(value, directed[(v, u)]) for (u, v), value in list(directed.items()))
        repeated = sum(value for pair, value in directed.items() if frozenset(pair) in old_pairs)
        result[cid] = dict(records_per_member_log=math.log1p(n / len(users)),
            active_day_fraction=len(days[cid]) / days_in_month,
            recent_record_fraction=recent[cid] / n if n else 0.0,
            top_member_fraction=max(now.values(), default=0) / n if n else 0.0,
            internal_reply_fraction=weight / authored_replies[cid] if authored_replies[cid] else 0.0,
            weighted_reciprocity=reciprocal / weight if weight else 0.0,
            activity_missing=int(n == 0), reply_missing=int(authored_replies[cid] == 0),
            returning_member_fraction=len({u for _, u in prior_active[cid]}) / len(users),
            past_active_month_fraction=len(prior_active[cid]) / (3 * len(users)),
            record_log_growth=math.log((1 + n) / (1 + before)),
            reply_log_growth=math.log((1 + weight) / (1 + old_weight)),
            repeated_dyad_fraction=repeated / weight if weight else 0.0,
            context_drift_js=_js(corpora[(month, cid)], corpora[(previous, cid)]),
            past_window_fraction=len(observed) / 3,
            context_history_missing=int(not n or not before), previous_reply_missing=int(old_weight == 0))
    return result
