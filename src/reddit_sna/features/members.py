"""Past-only member node attributes for group-node attention (HeTCo).

Each member of a month-t community receives attributes computed from records
authored in months <= t and from the month-t and t-1 reply graphs only.
Nothing from t+1, outgoing tracking links or labels is read.
"""

from collections import Counter, defaultdict
from contextlib import closing
import csv
import math

from reddit_sna.data.normalize import open_readonly

MEMBER_FEATURES = ("log_records", "log_strength", "internal_share", "log_partners",
                   "log_tenure", "previous_active", "corpus_count")
# v4 additions: network position and persistence relative to month t-1.
EXTENDED_FEATURES = ("log_coreness", "tie_persistence", "comember_persistence",
                     "log_bridging", "reciprocity", "observed_from_start")


def _edges(path, month):
    with path.open(encoding="utf-8", newline="") as stream:
        for edge in csv.DictReader(stream):
            if edge["month"] != month:
                raise ValueError("Reply graph row belongs to another month")
            yield edge["source_user_id"], edge["target_user_id"], float(edge["weight"])


def _coreness(partners):
    import igraph
    users = sorted(partners)
    index = {u: i for i, u in enumerate(users)}
    graph = igraph.Graph(n=len(users), edges=sorted({(index[u], index[v]) for u in users
                                                    for v in partners[u] if index[u] < index[v]}))
    return dict(zip(users, graph.coreness()))


def member_features(database, snapshots, months, groups, extended=False):
    """Return {(month, community_id): [[attributes...] per member, sorted by user]}.

    `groups[month][community_id]` is the member set. Tenure counts distinct
    earlier-or-current months with an authored record inside `months`;
    previous_active is 0 for the first month because no earlier month exists.
    With `extended`, EXTENDED_FEATURES follow MEMBER_FEATURES:
    coreness is the k-core number in undirected R_t; tie persistence is the share
    of t partners already partners at t-1; co-member persistence is the share of
    other current co-members who shared u's t-1 community; bridging counts
    other communities among u's t partners; reciprocity is the share of u's
    directed reply targets that also reply to u at t; observed_from_start flags
    users active in the first month, whose tenure is left-censored.
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
    previous_partners, previous_owner = {}, {}
    first_active = set(records[months[0]]) if months else set()
    for month in months:
        owners = {u: cid for cid, members in groups[month].items() for u in members}
        strength, internal, partners = Counter(), Counter(), defaultdict(set)
        for a, b, w in _edges(snapshots / month / "R.csv", month):
            for u, v in ((a, b), (b, a)):
                strength[u] += w
                partners[u].add(v)
                if u in owners and owners.get(v) == owners[u]:
                    internal[u] += w
        for user in records[month]:
            tenure[user] += 1
        if extended:
            core = _coreness(partners)
            targets, sources = defaultdict(set), defaultdict(set)
            for a, b, _ in _edges(snapshots / month / "directed_R.csv", month):
                targets[a].add(b)
                sources[b].add(a)
        for cid, members in groups[month].items():
            if extended:
                origin = Counter(previous_owner[v] for v in members if v in previous_owner)
            rows = []
            for u in sorted(members):
                row = [math.log1p(records[month][u]), math.log1p(strength[u]),
                       internal[u] / strength[u] if strength[u] else 0.0,
                       math.log1p(len(partners[u])), math.log1p(tenure[u]),
                       float(u in active_before), float(len(corpora[month][u]))]
                if extended:
                    before = previous_partners.get(u, set())
                    shared = origin[previous_owner[u]] - 1 if u in previous_owner else 0
                    row += [math.log1p(core.get(u, 0)),
                            len(partners[u] & before) / len(partners[u]) if partners[u] else 0.0,
                            shared / (len(members) - 1) if len(members) > 1 else 0.0,
                            math.log1p(len({owners[v] for v in partners[u] if v in owners} - {cid})),
                            len(targets[u] & sources[u]) / len(targets[u]) if targets[u] else 0.0,
                            float(u in first_active)]
                rows.append(row)
            output[(month, cid)] = rows
        active_before = set(records[month])
        previous_partners = {u: set(p) for u, p in partners.items()}
        previous_owner = owners
    return output
