"""Additive, monitored development-only continuity audit of sealed studies.

Never load final partitions, prediction targets, model objects or evaluation
stores here. Source artifacts are read-only; failed audit attempts are retained.
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import tomllib

from sklearn.metrics import adjusted_rand_score

from reddit_sna.data.archive import digest_file
from reddit_sna.data.normalize import open_readonly, month_boundary
from reddit_sna.data.observability import member_observations
from reddit_sna.evaluation.longitudinal import audit_rows, summarize
from reddit_sna.evaluation.temporal_protocol import months
from reddit_sna.pipelines.study_preparation import seal, verified
from reddit_sna.pipelines.study_resources import json_write, monitored
from reddit_sna.pipelines.study_samples import load_month, read_csv, write_csv
from reddit_sna.pipelines.temporal_study import _complete, _store


def implementation_hashes():
    """Bind executable audit modules independently of historical model freezes."""
    package = Path(__file__).parents[1]
    names = ('pipelines/longitudinal.py', 'evaluation/longitudinal.py', 'data/observability.py',
        'tracking/ged.py', 'contracts.py', 'pipelines/study_samples.py', 'pipelines/study_preparation.py',
        'data/normalize.py', 'graphs/audit.py')
    return {name: digest_file(package/name) for name in names}


def load_protocol(path):
    """Do not silently search thresholds, follow-up lengths or temporal cutoffs."""
    value = tomllib.loads(Path(path).read_text(encoding='utf-8'))
    expected = dict(schema_version=1, protocol_id='development-observability-v1',
        start='2015-01', cutoff_exclusive='2018-01', horizons=[1, 2, 3], alpha=.5, beta=.5,
        memory_budget_gib=8, working_budget_gib=30, minimum_free_gib=12)
    if value != expected:
        raise ValueError('Unsupported continuity audit protocol')
    return value


def seed_repeatability(directory, month, groups):
    """Recompute saved seed ARI on identical users, without rerunning Leiden.

    igraph reports NaN (stored as null) for degenerate cases. Keep that undefined
    value; sklearn's convention of 1 for identical trivial partitions is not a
    substitute. The statistic measures repeatability, never social accuracy.
    """
    import math
    detection = json.loads((directory/'detection.json').read_text(encoding='utf-8'))
    if (detection['actual_months'] != [month] or detection['gamma'] != 1 or
            detection['canonical_seed'] != 0 or [r['seed'] for r in detection['months'][0]['runs']] != [0, 1, 2]):
        raise ValueError('Incompatible detector repeatability source')
    owners = []
    for seed in (0, 1, 2):
        rows = read_csv(directory/f'memberships/{month}/membership-seed{seed}.csv')
        owner = {r['user_id']: r['community_id'] for r in rows}
        if len(owner) != len(rows) or any(r['month'] != month for r in rows):
            raise ValueError('Duplicate/inconsistent repeatability membership')
        owners.append(owner)
    users = sorted(set().union(*groups.values()))
    if any(set(owner) != set(users) for owner in owners):
        raise ValueError('Repeatability requires identical node universes')
    saved = detection['months'][0]['seed_pair_ARI']
    if len(saved) != 3:
        raise ValueError('Missing seed comparisons')
    result = []
    for index, (a, b) in enumerate(((0, 1), (0, 2), (1, 2))):
        value = saved[index]
        actual = adjusted_rand_score([owners[a][u] for u in users], [owners[b][u] for u in users])
        if value is not None and (not math.isfinite(value) or not math.isclose(value, actual, abs_tol=1e-10)):
            raise ValueError('Saved detector ARI does not reproduce')
        if value is None:
            # Confirm the undefined convention using the originating library.
            import igraph as ig
            raw = ig.compare_communities([int(owners[a][u].removeprefix('c')) for u in users],
                [int(owners[b][u].removeprefix('c')) for u in users], method='adjusted_rand')
            if math.isfinite(raw):
                raise ValueError('Saved undefined ARI is actually defined')
        result.append(dict(month=month, first_seed=a, second_seed=b, ari=value, users=len(users)))
    return result


def audit_study(study, output, protocol):
    """Verify, audit and seal a new destination; do not mutate the source study."""
    study, output = Path(study).resolve(), Path(output).resolve()
    source_hashes = implementation_hashes()
    if output.exists() or output.is_relative_to(study) or study.is_relative_to(output):
        raise ValueError('Audit output must be fresh and separate from source study')
    cutoff = protocol['cutoff_exclusive']
    store = _store(study, 'development')
    samples = _complete(study, 'development-samples')
    if store is None or samples is None:
        raise ValueError('Verified development store and samples required')
    store_info, sample_info = verified(store), verified(samples)
    ordered = months(protocol['start'], cutoff)
    if (store_info['stage'] != 'normalize' or store_info['end'] != cutoff or
            store_info['identity_scope'] != 'study-author-sha256-v1' or sample_info['months'] != ordered):
        raise ValueError('Only the complete development interval is supported')
    normalization = json.loads((store/'normalization.json').read_text(encoding='utf-8'))
    corpora = sorted(r['corpus'] for r in normalization['corpora'])
    if len(set(corpora)) != len(corpora) or not corpora:
        raise ValueError('Invalid normalized corpus inventory')
    database = store/'normalized.sqlite'
    with closing(open_readonly(database)) as db:
        if db.execute('SELECT COUNT(*) FROM records WHERE month>=? OR timestamp>=?',
                (cutoff, month_boundary(cutoff))).fetchone()[0]:
            raise ValueError('Future/final records in development source')
        if {r[0] for r in db.execute('SELECT DISTINCT corpus FROM records')} != set(corpora):
            raise ValueError('Mixed normalized corpus source')
    labels = {}
    for row in read_csv(samples/'labels.csv'):
        key = row['feature_month'], row['community_id']
        censored = (row.get('reason') == 'final_snapshot_censored' and
            row['feature_month'] == ordered[-1] and row['label_month'] == cutoff and
            row['label'] == '' and row['eligible'] == '0')
        if (key in labels or row['reference_id'] != sample_info['reference_id'] or
                row['feature_month'] not in ordered or (row['label_month'] >= cutoff and not censored)):
            raise ValueError('Duplicate/final/mixed-reference development label')
        labels[key] = row
    sources = {str(store): digest_file(store/'complete.json'), str(samples): digest_file(samples/'complete.json')}
    month_data, observations, repeatability = {}, {}, []
    for month in ordered:
        print(f'continuity audit: {month}', flush=True)
        directory = _complete(study, f'month-{month}')
        if directory is None or digest_file(directory/'complete.json') != sample_info['input_month_manifests'][month]:
            raise ValueError('Missing/changed/mixed development month')
        graph = json.loads((directory/'snapshots.json').read_text(encoding='utf-8'))
        if sorted(graph['declared_corpora']) != corpora:
            raise ValueError('Graph and normalization corpora differ')
        groups, edges = load_month(directory, month)
        observation = member_observations(database, month, corpora)
        if observation['reply_endpoints'] != set().union(*groups.values()):
            raise ValueError('Store observation and partition endpoint universes differ')
        month_data[month], observations[month] = (groups, edges), observation
        repeatability.extend(seed_repeatability(directory, month, groups))
        sources[str(directory)] = digest_file(directory/'complete.json')
    expected_keys = {(m, cid) for m, (groups, _) in month_data.items() for cid in groups}
    if set(labels) != expected_keys:
        raise ValueError('Development label/source key inventory differs')
    rows = audit_rows(month_data, observations, labels, sample_info['reference_id'], cutoff)
    windows, strata = summarize(rows)
    output.mkdir(parents=True)
    write_csv(output/'horizons.csv', rows)
    write_csv(output/'windows.csv', windows)
    write_csv(output/'repeatability.csv', repeatability)
    coverage = [dict(month=m, records=o['records'], empty_corpora=o['empty_corpora'],
        **{k: len(o[k]) for k in ('authored', 'posts', 'comments', 'reply_endpoints')}) for m, o in observations.items()]
    json_write(output/'summary.json', dict(protocol=protocol, reference_id=sample_info['reference_id'],
        sources=len(windows), horizon_rows=len(rows), strata=strata, coverage=coverage,
        horizon_support=[dict(horizon=h, sources=sum(r['horizon'] == h for r in rows),
            observed=sum(r['horizon'] == h and r['observation_status'] == 'observed' for r in rows),
            right_censored=sum(r['horizon'] == h and r['right_censored'] for r in rows),
            coverage_unknown=sum(r['horizon'] == h and not r['right_censored'] and r['coverage_unknown'] for r in rows)) for h in (1, 2, 3)],
        human_review='pending', interpretation='observed membership-match candidates, not social survival/death'))
    # Detect concurrent source drift before publishing a complete output.
    for path, digest in sources.items():
        verified(path)
        if digest_file(Path(path)/'complete.json') != digest:
            raise ValueError('Audit source changed while running')
    if implementation_hashes() != source_hashes:
        raise ValueError('Audit implementation changed while running')
    return seal(output, dict(status='complete', stage='longitudinal-audit',
        reference_id=sample_info['reference_id'], cutoff_exclusive=cutoff,
        sources=sources, implementation_sha256=source_hashes))


def run_audit(protocol_path, study, output, artifact_root):
    """Launch one monitored worker, preserving logs outside its sealed output."""
    protocol = load_protocol(protocol_path)
    output, artifact_root = Path(output).resolve(), Path(artifact_root).resolve()
    study = Path(study).resolve()
    if (not output.is_relative_to(artifact_root) or output == artifact_root or output.exists() or
            output.is_relative_to(study) or study.is_relative_to(output)):
        raise ValueError('Fresh output must be inside the artifact root')
    output.mkdir(parents=True)
    json_write(output/'protocol.json', protocol)
    command = [sys.executable, '-X', 'utf8', '-m', 'reddit_sna.pipelines.longitudinal',
        '--protocol', str(Path(protocol_path).resolve()), '--study', str(Path(study).resolve()), '--output', str(output/'audit')]
    monitored(command, output, 'audit', protocol)
    return verified(output/'audit')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for flag in ('protocol', 'study', 'output'):
        parser.add_argument('--'+flag, type=Path, required=True)
    args = parser.parse_args()
    audit_study(args.study, args.output, load_protocol(args.protocol))
