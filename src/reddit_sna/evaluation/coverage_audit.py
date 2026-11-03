"""Recipient-side coverage export from frozen inputs, without fitting or relabeling.

Reuse the shared diagnostic tables after enforcing reference, cutoff and terminal
snapshot contracts. No predictions, reviewer answers or coordinator keys are read.
"""

import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
from time import perf_counter

from reddit_sna.contracts import Event, next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.diagnostics import coverage_tables

IDENTITY = ('reference_id', 'feature_month', 'community_id')
EVENTS = {event.value for event in Event}
CENSORED = 'final_snapshot_censored'


def validate_coverage_inputs(features, labels, terminal_month):
    """Keep unresolved and censored distinct; reject silently mixed cohorts."""
    next_month(terminal_month)
    if not features or not labels:
        raise ValueError('Coverage requires nonempty features and labels')
    indexed = {}
    for row in features:
        key = tuple(row[k] for k in IDENTITY)
        next_month(key[1])
        size = float(row['size'])
        history = float(row['history_missing'])
        if (not all(isinstance(v, str) and v.strip() for v in key)
                or key in indexed or not math.isfinite(size) or size < 2 or not size.is_integer()
                or history not in (0., 1.)
                or row['available_through_month'] != row['feature_month']):
            raise ValueError('Invalid/duplicate feature key, size, history or cutoff')
        indexed[key] = row
    references = {key[0] for key in indexed}
    months = sorted({key[1] for key in indexed})
    if (len(references) != 1 or len(months) < 2 or terminal_month != months[-1]
            or any(next_month(a) != b for a, b in zip(months, months[1:]))):
        raise ValueError('Use one reference with consecutive months and the declared terminal snapshot')
    seen, label_references = set(), set()
    for row in labels:
        key = tuple(row[k] for k in IDENTITY)
        if key not in indexed or key in seen or row['label_month'] != next_month(key[1]):
            raise ValueError('Duplicate, missing or nonconsecutive label/feature join')
        seen.add(key)
        label_references.add(row['label_reference_id'])
        eligible, label, reason = str(row['eligible']), row['label'], row['reason']
        if not reason or eligible not in ('0', '1'):
            raise ValueError('Label requires explicit eligibility and reason')
        if 'size' in row and float(row['size']) != float(indexed[key]['size']):
            raise ValueError('Label and feature community sizes differ')
        if key[1] == terminal_month:
            if (eligible, label, reason) != ('0', '', CENSORED):
                raise ValueError('The terminal snapshot must remain censored, never dissolve')
        elif reason == CENSORED:
            raise ValueError('A nonterminal transition cannot be censored')
        elif eligible == '1' and label not in EVENTS:
            raise ValueError('Eligible rows need a resolved six-event label')
        elif eligible == '0' and label:
            raise ValueError('Unresolved rows cannot carry a resolved event')
    if (len(label_references) != 1 or not next(iter(label_references)).strip()
            or any(key[1] != terminal_month for key in set(indexed) - seen)):
        raise ValueError('Mixed label references or a missing nonterminal target')
    return dict(reference_id=next(iter(references)),
                label_reference_id=next(iter(label_references)), months=months,
                terminal_month=terminal_month, missing_terminal_targets=len(set(indexed) - seen))


def _read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, rows):
    fields = sorted(set().union(*(row.keys() for row in rows)))
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def run_coverage_audit(sample_run, output, terminal_month, *, manifest_name='complete.json',
                       month_directories=None):
    """Export coverage and graph evidence to a new directory, preserving inputs.

    Only features/labels and explicitly supplied monthly graph runs are consumed.
    The manifest must inventory the two tables. Terminal censoring is explicit,
    so a shorter/truncated source cannot silently invent a new period boundary.
    """
    started = perf_counter()
    source, output = Path(sample_run).resolve(), Path(output).resolve()
    if (output.exists() or output == source or output.is_relative_to(source)
            or source.is_relative_to(output)):
        raise ValueError('Use a new output directory separate from the source')
    if manifest_name not in ('complete.json', 'manifest.json'):
        raise ValueError('Choose a supported manifest filename')
    manifest = source / manifest_name
    metadata = json.loads(manifest.read_text(encoding='utf-8'))
    hashes = metadata.get('artifact_hashes', {})
    if metadata.get('status') != 'complete' or not hashes:
        raise ValueError('Source needs a completed hash inventory')
    pins = {manifest: digest_file(manifest)}
    for name in ('features.csv', 'labels.csv'):
        path = source / name
        expected = hashes.get(name)
        if not expected or digest_file(path) != expected:
            raise ValueError(f'Missing or changed source table: {name}')
        pins[path] = expected
    features, labels = _read_csv(source/'features.csv'), _read_csv(source/'labels.csv')
    contract = validate_coverage_inputs(features, labels, terminal_month)
    for field in ('reference_id', 'label_reference_id'):
        if field in metadata and metadata[field] != contract[field]:
            raise ValueError('Manifest and table references differ')
    if 'months' in metadata and metadata['months'] != contract['months']:
        raise ValueError('Manifest snapshot inventory differs from the feature table')
    graphs, graph_audit = {}, []
    month_directories = month_directories or {}
    if set(month_directories) - set(contract['months']):
        raise ValueError('Monthly graph selection is outside the sample cohort')
    if month_directories:
        if set(month_directories) != set(contract['months']):
            raise ValueError('Graph audit requires every feature month including the terminal one')
        from reddit_sna.pipelines.study_samples import load_month
        expected_months = metadata.get('input_month_manifests', {})
        for month, directory in sorted(month_directories.items()):
            directory = Path(directory).resolve()
            if output == directory or output.is_relative_to(directory) or directory.is_relative_to(output):
                raise ValueError('Graph inputs and output cannot overlap')
            complete = directory/'complete.json'
            if expected_months.get(month) != digest_file(complete):
                raise ValueError('Monthly graph manifest is not bound to this sample run')
            pins[complete] = digest_file(complete)
            groups, edges = load_month(directory, month)
            monthly_info = json.loads(complete.read_text(encoding='utf-8'))
            for name, expected_hash in monthly_info['artifact_hashes'].items():
                pins[(directory/name).resolve()] = expected_hash
            pairs = [frozenset((edge.source_user_id, edge.target_user_id)) for edge in edges]
            if len(pairs) != len(set(pairs)) or any(edge.month != month for edge in edges):
                raise ValueError('Duplicate or wrong-month graph edges')
            expected = {row['community_id']: int(float(row['size']))
                        for row in features if row['feature_month'] == month}
            if expected != {cid: len(members) for cid, members in groups.items()}:
                raise ValueError('Graph membership and feature community inventory/sizes differ')
            snapshot = directory/'snapshots.json'
            snapshot_info = json.loads(snapshot.read_text(encoding='utf-8'))
            records = [r for r in snapshot_info['months'] if r['month'] == month]
            if len(records) != 1:
                raise ValueError('Graph observation metadata needs exactly one matching month')
            record = records[0]
            for count in ('reply_endpoints', 'observed_users', 'active_authors', 'edge_covered_active_authors'):
                value = float(record[count])
                if not math.isfinite(value) or not value.is_integer() or value < 0:
                    raise ValueError('Invalid graph observation denominator')
            endpoints = sum(expected.values())
            if endpoints != int(record['reply_endpoints']):
                raise ValueError('Reply endpoints and assigned member count differ')
            for denominator, numerator, ratio in (
                    ('observed_users', endpoints, 'reply_coverage_observed_users'),
                    ('active_authors', int(record['edge_covered_active_authors']), 'reply_coverage_active_authors')):
                total = int(record[denominator])
                measured = record[ratio]
                if (numerator > total or numerator > endpoints
                        or (not total and measured is not None)
                        or (total and (measured is None or not math.isfinite(float(measured))
                            or not math.isclose(float(measured), numerator/total, rel_tol=1e-10, abs_tol=1e-12)))):
                    raise ValueError('Graph/user coverage does not match its declared denominator')
            graphs[month] = record
            graph_audit.append(dict(month=month, status='verified', communities=len(groups),
                                    members=endpoints, edges=len(edges)))
    tables, distributions = coverage_tables(labels, features, graphs or None)
    for row in tables + distributions:
        row.update(reference_id=contract['reference_id'], label_reference_id=contract['label_reference_id'])
    totals = next(row for row in tables if row['axis'] == 'all')
    totals['censored_member_months'] = sum(float(row['size']) for row in features
                                         if row['feature_month'] == terminal_month)
    for path, expected in pins.items():
        if digest_file(path) != expected:
            raise ValueError('An input changed during coverage processing')
    output.mkdir(parents=True, exist_ok=False)
    _write_csv(output/'coverage.csv', tables)
    if distributions:
        _write_csv(output/'distributions.csv', distributions)
    if graph_audit:
        _write_csv(output/'graph-audit.csv', graph_audit)
    missing = [] if graphs else ['Monthly sealed graph/membership/observation inputs were not supplied.']
    summary = dict(status='coverage_complete_graph_verified' if graphs else 'coverage_complete_graph_pending',
        **contract, totals=totals, graph_status='verified' if graphs else 'not_checked',
        missing_evidence=missing, human_review='pending_actual_independent_submissions',
        measured_pipeline_wall_seconds=perf_counter()-started,
        interpretation='Eligible/(eligible+unresolved); terminal censored excluded. '
                       'Size-weighted coverage counts member-months, not unique people. '
                       'Not event accuracy or population representativeness.')
    _write_json(output/'summary.json', summary)
    _write_json(output/'input-pins.json', {str(p): h for p, h in pins.items()})
    with (output/'REPORT.md').open('x', encoding='utf-8') as stream:
        stream.write('# Coverage audit\n\n'
            f"Reference: `{contract['reference_id']}`\n\n"
            f"Observed transitions: {totals['observed']}; eligible: {totals['eligible']}; "
            f"unresolved: {totals['unresolved']}; terminal censored: {totals['censored']}.\n\n"
            f"Community-month coverage: {totals['coverage']}. "
            f"Member-month coverage: {totals['member_month_coverage']}.\n\n"
            f"Graph audit: {summary['graph_status']}. Human review is pending actual submissions.\n\n"
            'See coverage.csv for feature-month, size and lineage-history strata. '
            'distributions.csv retains n, mean, q10, median and q90 when available. '
            'Censoring is not unresolved or dissolve. No model was fitted or label changed.\n')
    _write_json(output/'manifest.json', dict(status='complete', stage='recipient-coverage-audit',
        reference_id=contract['reference_id'], label_reference_id=contract['label_reference_id'],
        generated_utc=datetime.now(timezone.utc).isoformat(),
        source_manifest_sha256=pins[manifest],
        python_version=platform.python_version(),
        source_code_sha256={str(Path(__file__).resolve()): digest_file(Path(__file__)),
                            str(Path(__file__).with_name('diagnostics.py').resolve()):
                                digest_file(Path(__file__).with_name('diagnostics.py'))},
        artifact_hashes={p.name: digest_file(p) for p in sorted(output.iterdir()) if p.is_file()}))
    return summary
