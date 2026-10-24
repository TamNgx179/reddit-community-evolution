"""Read bounded observation channels from an immutable development store."""

from contextlib import closing

from reddit_sna.data.normalize import open_readonly
from reddit_sna.graphs.audit import VALID_REPLY


def member_observations(database, month, corpora):
    """Authorship is dated by the record; endpoints by the child's reply month.

    A parent can be older than the child. Restrict both records to the declared
    corpora, as in the graph source; no global account-activity claim follows.
    Zero records in any acquired corpus leaves coverage uncertain.
    """
    corpora = tuple(corpora)
    if not corpora or len(set(corpora)) != len(corpora):
        raise ValueError('Require a nonempty unique corpus declaration')
    placeholders = ','.join('?' for _ in corpora)
    result = dict(records=0, authored=set(), posts=set(), comments=set(), reply_endpoints=set())
    with closing(open_readonly(database)) as db:
        counts = dict(db.execute(f'SELECT corpus,COUNT(*) FROM records WHERE month=? AND corpus IN ({placeholders}) GROUP BY corpus', (month, *corpora)))
        result['records'] = sum(counts.values())
        result['empty_corpora'] = sorted(set(corpora) - set(counts))
        for uid, kind in db.execute(f'SELECT DISTINCT user_id,kind FROM records WHERE month=? AND corpus IN ({placeholders}) AND user_id IS NOT NULL', (month, *corpora)):
            result['authored'].add(uid)
            result['posts' if kind == 'post' else 'comments'].add(uid)
        for u, v in db.execute(f'''SELECT DISTINCT c.user_id,p.user_id FROM records c JOIN records p ON c.parent=p.id
                WHERE c.month=? AND c.kind='comment' AND c.corpus IN ({placeholders})
                AND p.corpus IN ({placeholders}) AND {VALID_REPLY}''', (month, *corpora, *corpora)):
            result['reply_endpoints'].update((u, v))
    return result
