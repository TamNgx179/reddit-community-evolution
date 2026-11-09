"""Accept frozen analysis exports and replay metrics without loading estimators.

The contract pins selected tables and historical manifests. A selected export
may omit unrelated artifacts from those manifests, so verification scope is
reported explicitly. Paths in the contract are relative to the current checkout.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import json
import math
from pathlib import Path, PurePosixPath
import platform
import hashlib
import zipfile
from time import perf_counter

from reddit_sna.contracts import next_month
from reddit_sna.data.archive import digest_file
from reddit_sna.evaluation.research import EVENTS, KEY, score

FEATURE_KEY = KEY[:3]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_rows(path):
    """Retain column order and reject malformed CSV records before joining."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"Missing or duplicate CSV columns: {path}")
        rows = list(reader)
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"Empty or malformed CSV: {path}")
    return fields, rows


def relative_path(root, name):
    """Resolve legacy separators while rejecting escapes and absolute payloads."""
    normalized = str(name).replace("\\", "/")
    parts = PurePosixPath(normalized)
    if parts.is_absolute() or not parts.parts or ".." in parts.parts or ":" in normalized:
        raise ValueError(f"Unsafe relative input: {name}")
    path = (Path(root) / normalized).resolve()
    if not path.is_relative_to(Path(root).resolve()) or path == Path(root).resolve():
        raise ValueError(f"Input escapes root: {name}")
    return path


def index_rows(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if any(not item.strip() for item in key) or key in result:
            raise ValueError("Empty or duplicate sample identity")
        result[key] = row
    return result


def verify_bindings(root, cohort):
    """Pin selected file bytes and validate each historical inventory's paths."""
    pins, manifests, paths = {}, {}, {}
    for name, binding in cohort["manifests"].items():
        path = relative_path(root, binding["path"])
        if digest_file(path) != binding["sha256"]:
            raise ValueError(f"Changed source manifest: {name}")
        info = json.loads(path.read_text(encoding="utf-8"))
        if info.get("status") not in ("complete", "complete_through_detection") or not info.get("artifact_hashes"):
            raise ValueError(f"Incomplete source manifest: {name}")
        for payload in info["artifact_hashes"]:
            relative_path(path.parent, payload)
        manifests[name] = path, info
        pins[binding["path"]] = binding["sha256"]
    for name, binding in cohort["files"].items():
        path = relative_path(root, binding["path"])
        expected = binding["sha256"]
        if digest_file(path) != expected:
            raise ValueError(f"Changed selected table/configuration: {name}")
        if "manifest" in binding:
            manifest_path, info = manifests[binding["manifest"]]
            inventory = {relative_path(manifest_path.parent, key): value
                         for key, value in info["artifact_hashes"].items()}
            if inventory.get(path) != expected:
                raise ValueError(f"Selected table is not bound to its manifest: {name}")
        pins[binding["path"]] = expected
        paths[name] = path
    return paths, pins


def verify_cohort(root, cohort):
    paths, pins = verify_bindings(root, cohort)
    protocol = json.loads(paths["protocol"].read_text(encoding="utf-8"))
    if protocol["seeds"] != cohort["seeds"]:
        raise ValueError("Seed contract differs from source protocol")
    boundary_field = cohort["boundary_field"]
    if protocol[boundary_field] != cohort["evaluation_start"]:
        raise ValueError("Evaluation split differs from source protocol")
    columns, features = read_rows(paths["features"])
    if columns != cohort["feature_columns"]:
        raise ValueError("Feature cache schema/order changed")
    _, labels = read_rows(paths["labels"])
    _, samples = read_rows(paths["samples"])
    fm, lm, sm = index_rows(features, FEATURE_KEY), index_rows(labels, KEY), index_rows(samples, KEY)
    terminal = cohort["terminal_month"]
    months = sorted({r["feature_month"] for r in features})
    if months[-1] != terminal or any(next_month(a) != b for a, b in zip(months, months[1:])):
        raise ValueError("Feature months are truncated or nonconsecutive")
    if {r["reference_id"] for r in features} != {cohort["reference_id"]}:
        raise ValueError("Feature references differ from frozen contract")
    for row in features:
        if row["available_through_month"] != row["feature_month"]:
            raise ValueError("Feature availability exceeds its declared month")
        if any(not math.isfinite(float(row[field])) for field in columns if field not in (*FEATURE_KEY, "available_through_month")):
            raise ValueError("Feature cache contains nonfinite values")
        size = float(row["size"])
        if size < 2 or not size.is_integer() or float(row["history_missing"]) not in (0, 1):
            raise ValueError("Invalid feature size/history flag")
    resolved = set()
    statuses = Counter()
    for key, row in lm.items():
        if (key[:3] not in fm or row["reference_id"] != cohort["reference_id"]
                or row["label_reference_id"] != cohort["label_reference_id"]
                or row["label_month"] != next_month(row["feature_month"])):
            raise ValueError("Label reference/key/month mismatch")
        if row["feature_month"] == terminal:
            if (row["eligible"], row["label"], row["reason"]) != ("0", "", "final_snapshot_censored"):
                raise ValueError("Terminal target must be censored")
            continue
        if row["eligible"] == "1" and row["label"] in EVENTS and row["reason"] != "final_snapshot_censored":
            resolved.add(key)
            statuses["resolved"] += 1
        elif row["eligible"] == "0" and not row["label"] and row["reason"] and row["reason"] != "final_snapshot_censored":
            statuses["unresolved"] += 1
        else:
            raise ValueError("Invalid target eligibility/status")
        if "size" in row and float(row["size"]) != float(fm[key[:3]]["size"]):
            raise ValueError("Label and feature sizes differ")
    nonterminal = {key for key in fm if key[1] != terminal}
    if {key[:3] for key in lm if key[1] != terminal} != nonterminal or sm.keys() != resolved:
        raise ValueError("Missing nonterminal label or resolved sample")
    if any(sm[key]["label"] != lm[key]["label"] for key in resolved):
        raise ValueError("Resolved sample truth differs from label table")
    statuses["censored"] = sum(key[1] == terminal for key in fm)
    units, predictions = {}, []
    for declaration in cohort["predictions"]:
        fields, records = read_rows(paths[declaration["file"]])
        if set(declaration["models"]) != {r["model"] for r in records}:
            raise ValueError("Prediction model schedule differs")
        for row in records:
            if "window" not in fields:
                if declaration.get("default_window") != "final" or set(cohort["windows"]) != {"final"}:
                    raise ValueError("Prediction window is ambiguous")
                row["window"] = "final"
            key = tuple(row[field] for field in KEY)
            unit = row["window"], row["model"], int(row["seed"])
            if (key not in resolved or row["y_true"] != lm[key]["label"] or row["y_pred"] not in EVENTS
                    or unit[0] not in cohort["windows"] or unit[2] not in cohort["seeds"]):
                raise ValueError("Prediction key/truth/window/seed mismatch")
            values = units.setdefault(unit, {})
            if key in values:
                raise ValueError("Duplicate keyed prediction")
            row.setdefault("fallback", "0")
            if row["fallback"] not in ("0", "1"):
                raise ValueError("Invalid fallback flag")
            values[key] = row
            predictions.append(row)
    expected_units = {(window, model, seed) for window in cohort["windows"]
                      for declaration in cohort["predictions"] for model in declaration["models"]
                      for seed in cohort["seeds"]}
    if units.keys() != expected_units:
        raise ValueError("Incomplete model/seed/window schedule")
    groups = []
    for (window, model, seed), values in sorted(units.items()):
        month_set = set(cohort["windows"][window])
        if window in ("final", "main") and any(month < cohort["evaluation_start"] for month in month_set):
            raise ValueError("Evaluation window overlaps earlier split")
        if window == "rolling" and sorted(month_set) != sorted(protocol["rolling_months"]):
            raise ValueError("Rolling schedule differs from source protocol")
        expected = {key for key in resolved if key[3] in month_set}
        if len(expected) != cohort["expected_window_n"][window] or values.keys() != expected:
            raise ValueError("Prediction window has missing/extra samples")
        groups.append(dict(window=window, model=model, seed=seed, n=len(values)))
    if {k: statuses[k] for k in cohort["expected_status_counts"]} != cohort["expected_status_counts"]:
        raise ValueError("Resolved/unresolved/censored cohort counts differ")
    observed = statuses["resolved"] + statuses["unresolved"]
    member_denominator = sum(float(fm[key[:3]]["size"]) for key in lm if key[1] != terminal)
    member_numerator = sum(float(fm[key[:3]]["size"]) for key in resolved)
    summary = dict(name=cohort["name"], reference_id=cohort["reference_id"],
                   label_reference_id=cohort["label_reference_id"], feature_columns=columns,
                   feature_rows=len(features), sample_rows=len(samples), status_counts=dict(statuses),
                   community_month_coverage=statuses["resolved"]/observed,
                   member_month_coverage=member_numerator/member_denominator,
                   terminal_month=terminal, groups=groups,
                   verification_scope="Selected analysis tables and bound manifests; unrelated historical payloads omitted.",
                   feature_cutoff="available_through_month equals feature_month",
                   fit_cutoff="Declared protocol only; training fit logs are outside selected table scope.")
    return summary, pins, predictions


def inspect_contract(repository, contract_path):
    root, path = Path(repository).resolve(), Path(contract_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Input contract must be within the checkout")
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("schema_version") != 1 or not contract.get("cohorts"):
        raise ValueError("Unsupported or empty acceptance contract")
    names = [c["name"] for c in contract["cohorts"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate cohort names")
    summaries, pins, predictions = [], {path.relative_to(root).as_posix(): digest_file(path)}, {}
    for cohort in contract["cohorts"]:
        summary, bound, records = verify_cohort(root, cohort)
        summaries.append(summary)
        pins.update(bound)
        predictions[cohort["name"]] = records
    missing = [name for name in contract.get("h1_required_paths", []) if not relative_path(root, name).exists()]
    dependency = dict(status="pending_missing_inputs" if missing else "available_not_verified",
                      missing_paths=missing, verification="Use Thanh's existing H1 verifier with complete real inputs.")
    return dict(cohorts=summaries, input_sha256=pins, h1_dependency=dependency), predictions


def verify_pins(root, pins):
    for name, expected in pins.items():
        if digest_file(relative_path(root, name)) != expected:
            raise ValueError(f"Input changed during acceptance: {name}")


def verify_bundle(path):
    """Check archived bytes without extracting potentially unsafe member paths."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate bundle entries")
        for name in names:
            relative_path(Path.cwd(), name)
        inventory = json.loads(archive.read("bundle-manifest.json"))
        if set(names) != set(inventory["sha256"]) | {"bundle-manifest.json"}:
            raise ValueError("Bundle inventory differs from payloads")
        for name, expected in inventory["sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Bundle payload changed: {name}")
    return inventory


def package_delivery(repository, replay, output):
    """Package only frozen selected exports, receipts and explicit product files.

    Raw content, reviewer answers and unlisted runtime directories are never
    discovered recursively. The archive preserves checkout-relative paths.
    """
    started = perf_counter()
    root, replay, output = map(lambda p: Path(p).resolve(), (repository, replay, output))
    if not replay.is_relative_to(root / "artifacts") or not output.is_relative_to(root / "dist"):
        raise ValueError("Use project artifacts for replay and dist for delivery")
    manifest = json.loads((replay / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("stage") != "frozen-prediction-replay" or manifest.get("status") != "complete":
        raise ValueError("Bundle requires completed Part 2")
    verify_pins(root, manifest["source_sha256"])
    receipt = json.loads((replay / "acceptance.json").read_text(encoding="utf-8"))
    verify_pins(root, receipt["input_sha256"])
    selected = {relative_path(root, name).relative_to(root).as_posix(): expected
                for name, expected in receipt["input_sha256"].items()}
    prior_dir = relative_path(root, receipt["part1_directory"])
    prior_manifest = prior_dir / "manifest.json"
    if digest_file(prior_manifest) != receipt["part1_manifest_sha256"]:
        raise ValueError("Part 1 manifest changed after replay")
    prior = json.loads(prior_manifest.read_text(encoding="utf-8"))
    for name, expected in prior["artifact_hashes"].items():
        path = relative_path(prior_dir, name)
        if digest_file(path) != expected:
            raise ValueError("Part 1 payload changed after replay")
        selected[path.relative_to(root).as_posix()] = expected
    selected[prior_manifest.relative_to(root).as_posix()] = digest_file(prior_manifest)
    for name, expected in manifest["artifact_hashes"].items():
        path = relative_path(replay, name)
        if digest_file(path) != expected:
            raise ValueError("Replay payload changed")
        selected[path.relative_to(root).as_posix()] = expected
    selected[(replay / "manifest.json").relative_to(root).as_posix()] = digest_file(replay / "manifest.json")
    product_files = ["pyproject.toml", "README.md", "docs/WEEK4_HANDOFF.md",
                     "scripts/verify_week4_inputs.py", "scripts/run_week4_acceptance.py",
                     "scripts/package_week4_handoff.py",
                     "src/reddit_sna/evaluation/artifact_acceptance.py",
                     "tests/unit/test_artifact_acceptance.py"]
    # Exact transitive source dependencies needed for table replay.
    product_files += ["src/reddit_sna/__init__.py", "src/reddit_sna/contracts.py",
                      "src/reddit_sna/data/__init__.py", "src/reddit_sna/data/archive.py",
                      "src/reddit_sna/evaluation/__init__.py", "src/reddit_sna/evaluation/research.py",
                      "src/reddit_sna/evaluation/research_protocol.py",
                      "src/reddit_sna/features/__init__.py", "src/reddit_sna/features/community.py",
                      "src/reddit_sna/features/history.py", "src/reddit_sna/features/context.py",
                      "src/reddit_sna/features/lagged.py", "src/reddit_sna/data/normalize.py"]
    for name in product_files:
        selected[name] = digest_file(relative_path(root, name))
    checksum = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or checksum.exists():
        raise FileExistsError("Delivery ZIP or checksum already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, expected in sorted(selected.items()):
            path = relative_path(root, name)
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != expected:
                raise ValueError("Selected source changed during packaging")
            archive.writestr(name, payload)
        archive.writestr("bundle-manifest.json", json.dumps(dict(schema_version=1,
            status="complete", wall_seconds=perf_counter()-started,
            scope="Selected frozen analysis exports, not full historical runtime or H1 verification",
            h1_dependency=receipt["h1_dependency"], sha256=selected), indent=2))
    verify_bundle(output)
    verify_pins(root, receipt["input_sha256"])
    with checksum.open("x", encoding="utf-8") as stream:
        stream.write(f"{digest_file(output)}  {output.name}\n")
    return output


def run_acceptance(repository, contract_path, output, *, accepted_input=None):
    """Part 1 accepts tables; Part 2 rechecks that receipt and replays scores."""
    started = perf_counter()
    root, output = Path(repository).resolve(), Path(output).resolve()
    if not output.is_relative_to(root/"artifacts") or output == root/"artifacts":
        raise ValueError("Use a new output beneath project artifacts")
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    input_files = [Path(contract_path).resolve()]
    for cohort in contract["cohorts"]:
        input_files.extend(relative_path(root, item["path"]) for item in cohort["files"].values())
        input_files.extend(relative_path(root, item["path"]) for item in cohort["manifests"].values())
    if any(output == p or output in p.parents or output.is_relative_to(p.parent) for p in input_files):
        raise ValueError("Acceptance output overlaps frozen inputs")
    if accepted_input is not None:
        receipt_dir = Path(accepted_input).resolve()
        if not receipt_dir.is_relative_to(root / "artifacts"):
            raise ValueError("Use a project artifacts receipt")
        if output == receipt_dir or output.is_relative_to(receipt_dir) or receipt_dir.is_relative_to(output):
            raise ValueError("Replay output overlaps its input receipt")
    output.mkdir(parents=True, exist_ok=False)
    try:
        receipt, predictions = inspect_contract(root, contract_path)
        if accepted_input is not None:
            prior_path = Path(accepted_input)/"manifest.json"
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            if prior.get("status") != "complete" or prior.get("stage") != "frozen-input-acceptance":
                raise ValueError("Replay requires a completed Part 1 record")
            for name, expected in prior["artifact_hashes"].items():
                if digest_file(relative_path(Path(accepted_input), name)) != expected:
                    raise ValueError("Part 1 receipt payload changed")
            accepted = json.loads((Path(accepted_input)/"acceptance.json").read_text(encoding="utf-8"))
            if accepted != receipt:
                raise ValueError("Part 1 receipt differs from current contract/inputs")
            result = []
            for cohort, records in predictions.items():
                units = defaultdict(list)
                for row in records:
                    units[row["window"], row["model"], int(row["seed"])].append(row)
                for (window, model, seed), rows in sorted(units.items()):
                    metrics = score(rows)
                    result.append(dict(cohort=cohort, window=window, model=model, seed=seed,
                                       n=metrics["n"], macro_f1_six=metrics["macro_f1_six"],
                                       balanced_accuracy=metrics["balanced_accuracy"],
                                       accuracy=sum(r["y_true"] == r["y_pred"] for r in rows)/len(rows)))
            with (output/"replayed-metrics.csv").open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(result[0]))
                writer.writeheader()
                writer.writerows(result)
            receipt["part1_manifest_sha256"] = digest_file(prior_path)
            receipt["part1_directory"] = receipt_dir.relative_to(root).as_posix()
        verify_pins(root, receipt["input_sha256"])
        write_json(output/"acceptance.json", receipt)
        (output/"run.log").write_text(
            f"Verified {len(receipt['cohorts'])} cohorts from frozen selected tables.\n"
            f"H1 dependency status: {receipt['h1_dependency']['status']}\n"
            f"Measured wall seconds: {perf_counter()-started:.6f}\n", encoding="utf-8")
        source = Path(__file__)
        write_json(output/"manifest.json", dict(status="complete",
            stage="frozen-prediction-replay" if accepted_input is not None else "frozen-input-acceptance",
            generated_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
            source_sha256={"src/reddit_sna/evaluation/artifact_acceptance.py": digest_file(source)},
            wall_seconds=perf_counter()-started,
            artifact_hashes={p.name: digest_file(p) for p in output.iterdir() if p.is_file()}))
        return receipt
    except Exception as error:
        write_json(output/"failure.json", dict(status="failed", error=str(error), wall_seconds=perf_counter()-started))
        raise
