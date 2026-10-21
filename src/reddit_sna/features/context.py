"""Cutoff-safe context on a fixed reply-community reference, without T cliques.

Only records authored in the feature month are read. Thread participant sets
therefore never include future completions of a conversation. These attributes
extend a forecasting prototype; they are not heterogeneous graph detection.
"""

from collections import Counter, defaultdict
from contextlib import closing
import math

from reddit_sna.contracts import next_month
from reddit_sna.data.archive import CORPORA
from reddit_sna.data.normalize import month_boundary, open_readonly

CONTEXT_FEATURES = ("subreddit_entropy", "thread_activity", "active_member_fraction",
                    "co_thread_external_exposure")


def context_features(database, month, groups):
    """Return four finite context attributes per community, including empty activity.

    Entropy uses authored-record corpus frequencies / log(15). Thread activity
    is log1p(unique community threads / community size). Exposure is the share
    of potential within-month thread peers outside the community, weighted by
    community participants; it is computed by counts, not quadratic pair lists.
    Participants include valid observed authors outside the assigned partition.
    """
    start, end = month_boundary(month), month_boundary(next_month(month))
    owners = {}
    for cid, members in groups.items():
        if not members or not cid:
            raise ValueError("Context communities must be nonempty")
        for user in members:
            if user in owners:
                raise ValueError("Context membership user assigned twice")
            owners[user] = cid
    counts = defaultdict(Counter)
    active = defaultdict(set)
    threads = defaultdict(set)
    with closing(open_readonly(database)) as db:
        # The WHERE clause prevents any future thread record being consumed.
        for user, root, corpus, timestamp in db.execute(
                "SELECT user_id,root,corpus,timestamp FROM records WHERE month=?", (month,)):
            if corpus not in CORPORA or not root or not start <= timestamp < end:
                raise ValueError("Context record has inconsistent corpus/month/root")
            if user is None:
                continue
            threads[root].add(user)
            if user in owners:
                cid = owners[user]
                counts[cid][corpus] += 1
                active[cid].add(user)
    roots = defaultdict(set)
    numerator, denominator = Counter(), Counter()
    for root, participants in threads.items():
        per_group = Counter(owners[u] for u in participants if u in owners)
        for cid, within in per_group.items():
            roots[cid].add(root)
            numerator[cid] += within * (len(participants) - within)
            denominator[cid] += within * (len(participants) - 1)
    result = {}
    for cid, members in groups.items():
        total = sum(counts[cid].values())
        entropy = -sum((n / total) * math.log(n / total) for n in counts[cid].values()) if total else 0.0
        result[cid] = dict(subreddit_entropy=entropy / math.log(len(CORPORA)),
                           thread_activity=math.log1p(len(roots[cid]) / len(members)),
                           active_member_fraction=len(active[cid]) / len(members),
                           co_thread_external_exposure=numerator[cid] / denominator[cid]
                           if denominator[cid] else 0.0)
    return result
