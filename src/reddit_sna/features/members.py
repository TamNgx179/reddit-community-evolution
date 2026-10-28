"""Past-only member node attributes for group-node attention (HeTCo v1).

Each member of a month-t community receives attributes computed from records
authored in months <= t and from the month-t reply graph R only. Nothing from
t+1, outgoing tracking links or labels is read.
"""

from collections import Counter, defaultdict
from contextlib import closing
import csv
import math

from reddit_sna.data.normalize import open_readonly

MEMBER_FEATURES = ("log_records", "log_strength", "internal_share", "log_partners",
                   "log_tenure", "previous_active", "corpus_count")


def member_features(database, snapshots, months, groups):
    """Return {(month, community_id): [[attributes...] per member, sorted by user]}.

    `groups[month][community_id]` is the member set. Tenure counts distinct
    earlier-or-current months with an authored record inside `months`;
    previous_active is 0 for the first month because no earlier month exists.
    """
    months = list(months)
    if months != sorted(set(months)):
        raise ValueError("Member feature months must be unique and ordered")
    records = defaultdict(Counter)
    corpora = defaultdict(lambda: defaultdict(set))
    with closing(open_readonly(database)) as db:
        for user, month, corpus in db.execute("SELECT user_id,month,corpus FROM records"):
            if user is None or month not in groups:
                continue
            records[month][user] += 1
            corpora[month][user].add(corpus)
    tenure, active_before, output = Counter(), set(), {}
    for month in months:
        owners = {u: cid for cid, members in groups[month].items() for u in members}
        strength, internal, partners = Counter(), Counter(), defaultdict(set)
        with (snapshots / month / "R.csv").open(encoding="utf-8", newline="") as stream:
            for edge in csv.DictReader(stream):
                if edge["month"] != month:
                    raise ValueError("Reply graph row belongs to another month")
                a, b, w = edge["source_user_id"], edge["target_user_id"], float(edge["weight"])
                for u, v in ((a, b), (b, a)):
                    strength[u] += w
                    partners[u].add(v)
                    if u in owners and owners.get(v) == owners[u]:
                        internal[u] += w
        for user in records[month]:
            tenure[user] += 1
        for cid, members in groups[month].items():
            output[(month, cid)] = [[
                math.log1p(records[month][u]), math.log1p(strength[u]),
                internal[u] / strength[u] if strength[u] else 0.0,
                math.log1p(len(partners[u])), math.log1p(tenure[u]),
                float(u in active_before), float(len(corpora[month][u])),
            ] for u in sorted(members)]
        active_before = set(records[month])
    return output
