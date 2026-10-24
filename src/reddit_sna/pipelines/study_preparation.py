"""Resumable study preparation; historical pilot contracts are untouched."""

import json
import math
from pathlib import Path

from reddit_sna.data.archive import CORPORA, audit_archives, digest_file, selected_archives
from reddit_sna.data.study import normalize_study
from reddit_sna.detection.leiden import detect_snapshots
from reddit_sna.graphs.snapshots import build_snapshots
from reddit_sna.pipelines.study_resources import json_write


def seal(directory, metadata):
    """Commit a stage inventory only after all outputs exist and hashes are known."""
    directory = Path(directory)
    metadata = dict(metadata, artifact_hashes={p.relative_to(directory).as_posix():digest_file(p)
        for p in sorted(directory.rglob('*')) if p.is_file() and p != directory / 'complete.json'})
    json_write(directory / 'complete.json', metadata)
    return metadata


def verified(directory):
    """Reject unsafe paths, incomplete stages, missing files and changed payloads."""
    directory = Path(directory).resolve()
    info = json.loads((directory / 'complete.json').read_text(encoding='utf-8'))
    if info.get('status') != 'complete' or not info.get('artifact_hashes'):
        raise ValueError('Study stage is incomplete')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
              if p.is_file() and p != directory / 'complete.json'}
    if actual != set(info['artifact_hashes']):
        raise ValueError('Study stage inventory differs')
    for name, expected in info['artifact_hashes'].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or digest_file(path) != expected:
            raise ValueError('Study stage hash mismatch')
    return info


def normalize_phase(raw, destination, end, source=None, *, corpora=CORPORA):
    """Audit original ZIPs and stream only metadata before the phase cutoff."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    if tuple(corpora) == CORPORA:
        paths = selected_archives(Path(raw), CORPORA)
    else:
        # External replication is an explicit fixed cohort. Do not relax the
        # historical selected_archives contract or mutate global constants.
        from reddit_sna.data.confirmation import declared_paths
        paths = sorted(declared_paths(raw, corpora))
    if source is None:
        audit = audit_archives(paths)
    else:
        source=Path(source)
        verified(source)
        audit=json.loads((source/'archive_audit.json').read_text(encoding='utf-8'))
        if [r['archive'] for r in audit['archives']]!=[p.name for p in paths]:
            raise ValueError('Extension archive inventory differs from verified development')
        for path,record in zip(paths,audit['archives']):
            if digest_file(path)!=record['sha256']:
                raise ValueError('Extension source archive changed')
    json_write(destination / 'archive_audit.json', audit)
    if source is None:
        summary = normalize_study(paths, destination / 'normalized.sqlite', end)
    else:
        from reddit_sna.data.study_extension import extend_study
        summary=extend_study(paths,source/'normalized.sqlite',destination/'normalized.sqlite',end)
    for path, record in zip(paths, audit['archives']):
        if digest_file(path) != record['sha256']:
            raise ValueError('Study archive changed during normalization')
    json_write(destination / 'normalization.json', summary)
    # Exact adapter bytes make metadata provenance independent of later work on
    # other model modules. Existing stage verification never trusts just HEAD.
    from reddit_sna.data import study, normalize, archive
    for module in (study, normalize, archive):
        source = Path(module.__file__)
        (destination / source.name).write_bytes(source.read_bytes())
    if summary.get('previous_cutoff'):
        from reddit_sna.data import study_extension
        (destination/'study_extension.py').write_bytes(Path(study_extension.__file__).read_bytes())
    return seal(destination, dict(status='complete', stage='normalize', end=end,
                                  identity_scope=summary['identity_scope']))


def prepare_month(database, destination, month, *, corpora=CORPORA):
    """Keep one month's graph in memory; outputs include complete loss audits."""
    from reddit_sna.contracts import next_month
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    graph = build_snapshots(Path(database), destination / 'snapshots', month, next_month(month), corpora=corpora)
    json_write(destination / 'snapshots.json', graph)
    detection = detect_snapshots(destination / 'snapshots', destination / 'memberships',
        graph['identity_scope'], seeds=(0,1,2), gamma=1.0,
        graph_protocol=graph['graph_protocol'], expected_months=[month])
    for summary in detection['months']:
        # igraph reports NaN ARI for some degenerate one-community partitions.
        # Preserve this as explicitly unavailable, not an invented stability1.
        summary['seed_pair_ARI']=[value if math.isfinite(value) else None for value in summary['seed_pair_ARI']]
        summary['seed_pair_ARI_note']='null denotes undefined igraph ARI for a degenerate partition'
    json_write(destination / 'detection.json', detection)
    return seal(destination, dict(status='complete', stage='month', month=month,
                                  graph_reference=graph['graph_reference']))
