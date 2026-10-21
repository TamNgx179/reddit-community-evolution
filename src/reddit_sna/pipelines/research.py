"""Run the midterm proposed forecasting experiment on a fixed core reference.

The old three pair demos are inputs neither to one another nor to this command
implicitly. Here the caller explicitly supplies a verified Reddit preparation
and core forecast. Outcomes are descriptive development evidence only.
"""

import csv
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
from time import perf_counter

import joblib
from threadpoolctl import threadpool_limits

from reddit_sna.artifacts import capture_run_provenance, source_snapshot
from reddit_sna.config import validate_run_id
from reddit_sna.data.archive import digest_file
from reddit_sna.data.normalize import open_readonly
from reddit_sna.evaluation.research import KEY, analyze_predictions
from reddit_sna.evaluation.research_protocol import load_protocol, resolved_protocol, VARIANTS
from reddit_sna.features.context import context_features
from reddit_sna.features.lagged import predecessor_features
from reddit_sna.models.research import fit_variant, predict_variant
from reddit_sna.reporting.forecast_handoff import read_handoff
from reddit_sna.reporting.handoff import inspect_handoff


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_table(path, rows, fields=None):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_table(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _sources(preparation, forecast, artifact_root):
    """Validate all public artifacts, then bind forecast to this exact source."""
    if not preparation.is_relative_to(artifact_root) or not forecast.is_relative_to(artifact_root):
        raise ValueError("Research sources must remain inside project artifacts")
    accepted = inspect_handoff(preparation, preparation, artifact_root)
    delivery = read_handoff(forecast)
    fm = delivery["manifest"]
    if (set(fm["source_manifests"].values()) != {digest_file(preparation / "manifest.json")}
            or {r["reference_id"] for r in delivery["samples"]} != {accepted["canonical_reference"]}
            or not fm.get("history") or fm["tracker"] != "ged-strength-topology-v1"):
        raise ValueError("Research requires matched GED/history forecast and preparation reference")
    with closing(open_readonly(preparation / "normalized.sqlite")) as db:
        provenance = dict(db.execute("SELECT key,value FROM provenance"))
    snapshot = json.loads((preparation / "snapshots.json").read_text(encoding="utf-8"))
    if (provenance.get("identity_scope") != snapshot["identity_scope"]
            or provenance.get("end_month_exclusive") != snapshot["end_month_exclusive"]):
        raise ValueError("SQLite identity scope/cutoff differs from membership source")
    return delivery


def run_research(protocol_path, preparation, forecast, artifact_root, run_id):
    """Write the protocol before fitting and retain failed status on any error."""
    started = perf_counter()
    protocol_path, preparation, forecast, artifact_root = map(
        lambda p: Path(p).resolve(), (protocol_path, preparation, forecast, artifact_root))
    protocol = load_protocol(protocol_path)
    validate_run_id(run_id)
    output = artifact_root / "research" / run_id
    if output.exists() or not output.resolve().is_relative_to(artifact_root):
        raise ValueError("Research output exists or escapes artifacts")
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in (preparation, forecast)):
        raise ValueError("Research output must not overlap its sources")
    source = _sources(preparation, forecast, artifact_root)
    if source["manifest"]["test_start_label_month"] != protocol["test_start"]:
        raise ValueError("Research holdout must match the supplied core split")
    months = source["manifest"]["actual_months"]
    label_months = sorted({r["label_month"] for r in source["samples"]})
    if (not set(protocol["rolling_months"]).issubset(label_months)
            or protocol["rolling_months"][0] <= label_months[0]
            or len([m for m in label_months if m >= protocol["test_start"]]) != 3):
        raise ValueError("Research requires supported six rolling months and three main holdout months")
    package = Path(__file__).parents[1]
    code_hashes = {p.relative_to(package).as_posix(): digest_file(p) for p in package.rglob("*.py")}
    captured_source, captured_environment, source_blobs = capture_run_provenance()
    pins = {str(p): digest_file(p) for p in (protocol_path, preparation / "manifest.json", forecast / "manifest.json")}
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(status="started", schema_version=1, artifact_type="midterm-research",
                    source_manifests=pins, source_hashes=code_hashes,
                    source_preparation=str(preparation), source_forecast=str(forecast),
                    label_reference_id=source["manifest"]["label_reference_id"],
                    sample_count=len(source["samples"]), dataset="Reddit 2015 inspected pilot",
                    git=captured_source["git"], source_archive=captured_source["files"],
                    environment=captured_environment,
                    python=platform.python_version(), dependencies={n: version(n) for n in
                    ("numpy", "scikit-learn", "joblib", "threadpoolctl")},
                    native_peak_memory_mb=None, memory_reason="native peak process memory not measured",
                    human_annotation="pending", unseen=False, novelty="unverified")
    save_json(output / "manifest.json", manifest)
    try:
        # Archive the actual code bytes because the verified run precedes its
        # reviewed commit. Git HEAD alone cannot reproduce an uncommitted change.
        for relative, blob in source_blobs.items():
            target = output / "provenance/source" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        (output / "protocol.toml").write_bytes(protocol_path.read_bytes())
        save_json(output / "protocol.json", resolved_protocol(protocol))
        manifest["protocol_frozen_at"] = datetime.now(timezone.utc).isoformat()
        manifest["protocol_sha256"] = digest_file(output / "protocol.json")
        save_json(output / "manifest.json", manifest)
        groups = {}
        features = {(r["feature_month"], r["community_id"]): r for r in source["features"]}
        detection = json.loads((preparation / "detection.json").read_text(encoding="utf-8"))
        for month in months:
            groups[month] = {}
            for r in read_table(preparation / f"memberships/{month}/membership-seed{detection['canonical_seed']}.csv"):
                groups[month].setdefault(r["community_id"], set()).add(r["user_id"])
        lags = predecessor_features(months, features, source["labels"], read_table(forecast / "tracking.csv"))
        contexts = {m: context_features(preparation / "normalized.sqlite", m, groups[m]) for m in months}
        samples = []
        for r in source["samples"]:
            month, cid = r["feature_month"], r["community_id"]
            lag, event = lags[(month, cid)]
            samples.append({**r, **contexts[month][cid], **lag, "past_event": event,
                            "label_reference_id": manifest["label_reference_id"]})
        write_table(output / "samples.csv", samples)
        save_json(output / "quality.json", source["quality"])
        predictions, fits = [], []
        manifest["first_fit_at"] = datetime.now(timezone.utc).isoformat()
        save_json(output / "manifest.json", manifest)
        (output / "models").mkdir()
        windows = [("main", protocol["test_start"]),
                   *[("rolling", month) for month in protocol["rolling_months"]]]
        # Limit numerical-library threads for predictable resource use; model
        # schedules and feature order are fixed independently of observed scores.
        with threadpool_limits(limits=1):
            for window, boundary in windows:
                train = [r for r in samples if r["label_month"] < boundary]
                test = [r for r in samples if r["label_month"] >= boundary] if window == "main" else [
                    r for r in samples if r["label_month"] == boundary]
                for seed in protocol["seeds"]:
                    for name in VARIANTS:
                        fit_start = perf_counter()
                        fitted = fit_variant(name, train, seed)
                        predicted, fallback = predict_variant(fitted, test)
                        model_file = f"models/{window}-{boundary}-{name}-{seed}.joblib"
                        joblib.dump(fitted, output / model_file)
                        # Reload only the trusted file written by this invocation.
                        if predict_variant(joblib.load(output / model_file), test) != (predicted, fallback):
                            raise ValueError("Reloaded research model predictions differ")
                        fits.append(dict(window=window, boundary=boundary, seed=seed, model=name,
                                         model_file=model_file, train_n=len(train), test_n=len(test),
                                         train_label_months=sorted({r['label_month'] for r in train}),
                                         features=list(fitted["fields"]), single_class_fallback=fitted["single_class_fallback"],
                                         wall_seconds=perf_counter() - fit_start))
                        predictions.extend({**{k: row[k] for k in KEY}, "window": window, "model": name,
                                            "seed": seed, "y_true": row["label"], "y_pred": str(pred),
                                            "fallback": flag} for row, pred, flag in zip(test, predicted, fallback))
        write_table(output / "predictions.csv", predictions)
        save_json(output / "fits.json", fits)
        summary = analyze_predictions(predictions, protocol)
        save_json(output / "evaluation.json", summary)
        write_table(output / "comparison.csv", summary["means"])
        # Validate data/source bytes again, not just the parent manifest bytes.
        _sources(preparation, forecast, artifact_root)
        if any(digest_file(Path(p)) != h for p, h in pins.items()) or code_hashes != {
                p.relative_to(package).as_posix(): digest_file(p) for p in package.rglob("*.py")}:
            raise ValueError("Research source/config changed during execution")
        if source_snapshot()[2] != captured_source["files"]:
            raise ValueError("Research package/build metadata changed during execution")
        manifest.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat(),
                        wall_seconds=perf_counter() - started,
                        artifact_hashes={p.relative_to(output).as_posix(): digest_file(p)
                                         for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"})
        save_json(output / "manifest.json", manifest)
        from reddit_sna.reporting.research import read_research
        read_research(output)
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__, wall_seconds=perf_counter() - started)
        save_json(output / "manifest.json", manifest)
        raise
    return output
