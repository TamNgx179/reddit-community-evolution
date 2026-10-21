"""Verify the midterm research handoff and draw its actual stored predictions."""

import csv
from datetime import datetime
import json
import math
from pathlib import Path

from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import KEY, EVENTS, analyze_predictions
from reddit_sna.evaluation.research_protocol import load_protocol, resolved_protocol, VARIANTS, FULL


def _rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("Research CSV row width differs from schema")
    return rows


def read_research(run):
    """Check hashes, complete sample joins, fit schedules and independent scores.

    Integrity is relative to trusted manifest bytes, not authentication against
    simultaneous alteration of all files and metadata. Never unpickle in a
    reporting consumer. Model reload is verified by the producer/audit instead.
    """
    run = Path(run).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("status") != "complete" or manifest.get("schema_version") != 1
            or manifest.get("artifact_type") != "midterm-research"):
        raise ValueError("A complete midterm research run is required")
    hashes = manifest.get("artifact_hashes", {})
    required = {"protocol.toml", "protocol.json", "samples.csv", "quality.json", "predictions.csv",
                "fits.json", "evaluation.json", "comparison.csv"}
    actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.name != "manifest.json"}
    if not required.issubset(hashes) or set(hashes) != actual:
        raise ValueError("Research artifact inventory is incomplete")
    for relative, expected in hashes.items():
        path = (run / relative).resolve()
        if not path.is_relative_to(run) or digest_file(path) != expected:
            raise ValueError("Research artifact hash mismatch or unsafe path")
    archived = manifest.get('source_archive', {})
    if not archived or not manifest.get('git'):
        raise ValueError('Research source archive/Git provenance is missing')
    for relative, digest in archived.items():
        if hashes.get('provenance/source/' + relative) != digest:
            raise ValueError('Research archived source differs from provenance')
    protocol = load_protocol(run / "protocol.toml")
    resolved = json.loads((run / "protocol.json").read_text(encoding="utf-8"))
    if resolved != resolved_protocol(protocol) or digest_file(run / "protocol.json") != manifest["protocol_sha256"]:
        raise ValueError("Research resolved protocol differs from frozen settings")
    if datetime.fromisoformat(manifest["protocol_frozen_at"]) > datetime.fromisoformat(manifest["first_fit_at"]):
        raise ValueError("Research protocol was not frozen before fitting")
    samples, rows = _rows(run / "samples.csv"), _rows(run / "predictions.csv")
    keys = {tuple(r[k] for k in KEY): r for r in samples}
    if len(keys) != len(samples) or len(samples) != manifest["sample_count"]:
        raise ValueError("Research samples contain duplicate/missing keys")
    for r in samples:
        if (r["label"] not in EVENTS or r["past_event"] not in ("", *EVENTS)
                or r["label_reference_id"] != manifest["label_reference_id"]
                or any(not math.isfinite(float(r[f])) for f in FULL)):
            raise ValueError("Research sample labels/features/reference invalid")
    for row in rows:
        row["seed"] = int(row["seed"])
        row["fallback"] = int(row["fallback"])
        key = tuple(row[k] for k in KEY)
        if key not in keys or row["y_true"] != keys[key]["label"]:
            raise ValueError("Research prediction/truth sample join differs")
    for window in ("main", "rolling"):
        expected = {k for k, r in keys.items() if r["label_month"] >= protocol["test_start"]} if window == "main" else {
            k for k, r in keys.items() if r["label_month"] in protocol["rolling_months"]}
        if {tuple(r[k] for k in KEY) for r in rows if r["window"] == window} != expected:
            raise ValueError("Research predictions omit evaluation samples")
    result = analyze_predictions(rows, protocol)
    if result != json.loads((run / "evaluation.json").read_text(encoding="utf-8")):
        raise ValueError("Research evaluation differs from independently computed predictions")
    comparison = _rows(run / "comparison.csv")
    if len(comparison) != len(result["means"]):
        raise ValueError("Research comparison table support differs")
    for actual_row, wanted in zip(comparison, result["means"]):
        if any(str(wanted[k]) != v for k, v in actual_row.items()) or set(actual_row) != set(wanted):
            raise ValueError("Research comparison table differs from predictions")
    fits = json.loads((run / "fits.json").read_text(encoding="utf-8"))
    expected_fits = {(w, b, name, seed) for w, b in [("main", protocol["test_start"]),
                     *[("rolling", m) for m in protocol["rolling_months"]]]
                     for name in VARIANTS for seed in protocol["seeds"]}
    found = set()
    for fit in fits:
        key = fit["window"], fit["boundary"], fit["model"], fit["seed"]
        if key not in expected_fits or key in found:
            raise ValueError("Research fit schedule differs")
        found.add(key)
        train = [r for r in samples if r["label_month"] < fit["boundary"]]
        test = [r for r in samples if r["label_month"] >= fit["boundary"]] if fit["window"] == "main" else [
            r for r in samples if r["label_month"] == fit["boundary"]]
        if (fit["train_n"] != len(train) or fit["test_n"] != len(test)
                or fit["features"] != list(VARIANTS[fit["model"]])
                or fit["train_label_months"] != sorted({r["label_month"] for r in train})
                or fit["single_class_fallback"] != (len({r['label'] for r in train}) < 2)
                or fit["model_file"] not in hashes):
            raise ValueError("Research fit availability/budget/sample metadata differs")
    if found != expected_fits or {f['model_file'] for f in fits} != {p for p in hashes if p.startswith('models/')}:
        raise ValueError("Research model inventory differs from fit schedule")
    # A1 intentionally equals B5, so a differing result signals a budget/reference bug.
    b5 = {(r["window"], r["seed"], *(r[k] for k in KEY)): r["y_pred"]
          for r in rows if r["model"] == "B5_matched_boosting"}
    a1 = {(r["window"], r["seed"], *(r[k] for k in KEY)): r["y_pred"]
          for r in rows if r["model"] == "A1_no_context"}
    if b5 != a1:
        raise ValueError("Matched A1 and B5 predictions must be identical")
    quality = json.loads((run / "quality.json").read_text(encoding="utf-8"))
    if quality["eligible_samples"] != len(samples) or quality["label_reference_id"] != manifest["label_reference_id"]:
        raise ValueError("Research quality population differs")
    return dict(manifest=manifest, protocol=protocol, samples=samples, predictions=rows,
                evaluation=result, fits=fits, quality=quality)


def build_figures(delivery):
    """Seven figure families from verified artifacts; never hardcode scores."""
    import numpy as np
    from collections import Counter
    import matplotlib.pyplot as plt
    ev = delivery["evaluation"]
    main = [r for r in ev["means"] if r["window"] == "main"]
    names = [r["model"] for r in main]
    figures = {}
    fig, ax = plt.subplots(figsize=(10, 4))
    for split, offset in (("train", -.18), ("test", .18)):
        counts = Counter(r['label'] for r in delivery['samples'] if
                         (r['label_month'] < delivery['protocol']['test_start']) == (split == 'train'))
        ax.bar(np.arange(6) + offset, [counts[e] for e in EVENTS], .36, label=split)
    ax.set_xticks(np.arange(6), EVENTS); ax.set_ylabel('Eligible samples'); ax.legend()
    ax.set_title('Fixed GED pseudo-label population; excluded transitions retained in quality.json')
    figures['population'] = fig
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.barh(names[::-1], [r['mean_macro_f1_six'] for r in main][::-1])
    ax.set_xlabel('Mean fixed-six-class macro-F1 across three seeds')
    ax.set_title('Inspected 2015 main holdout; descriptive performance')
    figures['comparison'] = fig
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.barh(names[::-1], [r['delta_vs_B5'] for r in main][::-1]); ax.axvline(0, color='black')
    ax.set_xlabel('Paired score difference versus matched B5'); ax.set_title('Context/history/lag ablations; negative results retained')
    figures['ablations'] = fig
    fig, ax = plt.subplots(figsize=(10, 4))
    for name in ('B5_matched_boosting', 'HeTCo_v0', 'A4_no_dynamics', 'A6_no_lag'):
        values = [np.mean([r['macro_f1_six'] for r in ev['monthly'] if
                          r['window'] == 'rolling' and r['model'] == name and r['month'] == month])
                  for month in delivery['protocol']['rolling_months']]
        ax.plot(delivery['protocol']['rolling_months'], values, marker='o', label=name)
    ax.set_ylabel('Mean six-class macro-F1'); ax.set_title('Rolling origins: fit earlier label months only'); ax.legend()
    figures['monthly'] = fig
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, name in zip(axes, ('B5_matched_boosting', 'HeTCo_v0')):
        matrix = next(r['confusion'] for r in ev['scores'] if r['window'] == 'main' and r['model'] == name and r['seed'] == 42)
        ax.imshow(matrix, cmap='Blues'); ax.set_xticks(range(6), EVENTS, rotation=45, ha='right')
        ax.set_yticks(range(6), EVENTS); ax.set_title(name + ' / seed 42'); ax.set_xlabel('Predicted'); ax.set_ylabel('Truth')
        for i in range(6):
            for j in range(6): ax.text(j, i, str(matrix[i][j]), ha='center', va='center', fontsize=8)
    figures['confusion'] = fig
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, field in zip(axes, ('subreddit_entropy', 'co_thread_external_exposure')):
        ax.hist([float(r[field]) for r in delivery['samples']], bins=20); ax.set_xlabel(field)
        ax.set_ylabel('Eligible communities'); ax.set_title('Observed context distribution')
    figures['context'] = fig
    fig, ax = plt.subplots(figsize=(10, 4))
    intervals = ev['uncertainty']['intervals']
    selected = ['HeTCo_v0', 'A1_no_context', 'A4_no_dynamics', 'A6_no_lag']
    for i, name in enumerate(selected):
        lo, hi = intervals[name]['low'], intervals[name]['high']
        estimate = next(r['delta_vs_B5'] for r in ev['means'] if r['window'] == 'rolling' and r['model'] == name)
        ax.plot([lo, hi], [i, i], marker='|'); ax.plot(estimate, i, 'o')
    ax.axvline(0, color='black'); ax.set_yticks(range(len(selected)), selected)
    ax.set_xlabel('Exploratory 95% block-bootstrap delta interval versus B5')
    ax.set_title('Six inspected rolling months; limited support; not confirmatory')
    figures['uncertainty'] = fig
    for fig in figures.values(): fig.tight_layout()
    return figures


def export_figures(run, output):
    """Export into a new sibling output; never modify the completed source run."""
    run, output = Path(run).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError('Research figure output must be new and separate from run')
    delivery = read_research(run)
    figures = build_figures(delivery)
    import matplotlib.pyplot as plt
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, fig in figures.items():
            for extension in ('png', 'svg'): fig.savefig(output / f'{name}.{extension}', dpi=140)
        (output/'manifest.json').write_text(json.dumps(dict(status='complete', source_manifest_sha256=digest_file(run/'manifest.json'),
            figures=list(figures), files={p.name:digest_file(p) for p in output.iterdir() if p.is_file()}),indent=2)+'\n',encoding='utf-8')
    finally:
        for fig in figures.values(): plt.close(fig)
    return output
