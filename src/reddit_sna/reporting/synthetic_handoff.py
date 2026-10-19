"""Read-only, stdlib consumer of PHUC-005 synthetic benchmark runs.

Checks file integrity and the graph/truth/detector CSV contracts without
importing a producer, graph backend or metric library. Metrics and frozen
runtime provenance are inventoried, not recomputed or re-certified here.
Can also run as a standalone file: python -I -S <this-file> RUN --output NEW.
"""

import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path, PurePosixPath
import re
import sys


SCENARIOS = ("stable", "grow", "shrink", "merge", "split", "dissolve")
PROTOCOL = "synthetic-planted-undirected-v1"
MEMBERSHIP = "reference_id,month,community_id,user_id"
SNAPSHOT_COLUMNS = (
    "dataset_id,split,scenario,generator_seed,month,detector_seed,canonical,"
    "truth_reference,detector_reference,nodes_file,graph_file,truth_membership_file,"
    "truth_events_file,truth_links_file,detector_membership_file,active_nodes,"
    "endpoint_nodes,isolated_nodes,truth_communities,predicted_communities"
).split(",")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"nonstandard JSON number: {value}")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique,
                      parse_constant=_constant)


def _digest(path):
    return sha256(path.read_bytes()).hexdigest()


def _path(root, name):
    _require(isinstance(name, str) and name and "\\" not in name and ":" not in name,
             "unsafe relative path")
    relative = PurePosixPath(name)
    _require(relative.parts and not relative.is_absolute() and relative.as_posix() == name
             and all(p not in (".", "..") for p in relative.parts), "unsafe relative path")
    path = root / name
    _require(path.resolve().is_relative_to(root.resolve()), "path escapes package")
    _require(not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)),
             "symlink is not a handoff file")
    return path


def _inventory(root, excluded):
    files = {}
    for path in sorted(root.rglob("*")):
        _require(not path.is_symlink(), "symlink is not a handoff file")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            _path(root, name)
            if name not in excluded:
                data = path.read_bytes()
                files[name] = {"sha256": sha256(data).hexdigest(), "bytes": len(data)}
    return files


def _check_files(root, declared, excluded, *, sizes=False):
    _require(isinstance(declared, dict) and declared, "missing file inventory")
    actual = _inventory(root, excluded)
    _require(set(declared) == set(actual), "file inventory mismatch")
    for name, info in declared.items():
        _path(root, name)
        _require(isinstance(info, dict) and info.get("sha256") == actual[name]["sha256"],
                 f"file hash mismatch: {name}")
        if sizes:
            _require(type(info.get("bytes")) is int and info["bytes"] == actual[name]["bytes"],
                     f"file size mismatch: {name}")
    return actual


def _table(path, header):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        columns = header.split(",")
        _require(next(reader, None) == columns, f"CSV schema mismatch: {path.name}")
        rows = list(reader)
    _require(all(len(row) == len(columns) and all(v.strip() for v in row) for row in rows),
             f"invalid CSV row: {path.name}")
    return rows


def _members(path, reference, users):
    partitions = {month: {} for month in users}
    for ref, month, group, user in _table(path, MEMBERSHIP):
        _require(ref == reference and month in users, "membership reference/month mismatch")
        _require(user not in partitions[month], "duplicate membership user key")
        partitions[month][user] = group
    _require(all(set(partitions[m]) == set(users[m]) for m in users),
             "membership user coverage/endpoint mismatch")
    return partitions


def _months(values):
    _require(isinstance(values, list) and len(values) == 2
             and all(isinstance(m, str) and re.fullmatch(r"\d{4}-\d{2}", m) for m in values),
             "expected two observed months")
    first, second = (date.fromisoformat(m + "-01") for m in values)
    _require(second == date(first.year + (first.month == 12), first.month % 12 + 1, 1),
             "observed months must be consecutive")
    return values


def _transitions(source, reference, months, truth):
    groups = {m: set(truth[m].values()) for m in months}
    events = {}
    for ref, sm, group, tm, event in _table(source / "truth/events.csv",
            "reference_id,source_month,source_community_id,target_month,event"):
        _require(ref == reference and [sm, tm] == months and group in groups[sm]
                 and event in SCENARIOS, "truth event reference/key/label mismatch")
        _require(group not in events, "duplicate truth event source")
        events[group] = event
    _require(set(events) == groups[months[0]], "truth events must cover every source group")
    links = set()
    for ref, sm, group, tm, target in _table(source / "truth/links.csv",
            "reference_id,source_month,source_community_id,target_month,target_community_id"):
        _require(ref == reference and [sm, tm] == months and group in groups[sm]
                 and target in groups[tm], "truth link reference/key mismatch")
        _require((group, target) not in links, "duplicate truth link")
        links.add((group, target))
    for group, event in events.items():
        targets = {target for src, target in links if src == group}
        _require((len(targets) == 0 if event == "dissolve" else
                  len(targets) >= 2 if event == "split" else len(targets) == 1),
                 "truth event/link cardinality mismatch")
    return len(events), len(links)


def _dataset(root, dataset_id, recipe, split, record):
    source = root / "inputs/source" / dataset_id
    detected = root / "inputs/detected" / dataset_id
    gm, dm = _json(source / "metadata.json"), _json(detected / "metadata.json")
    for meta, kind in ((gm, "synthetic-graph-truth"), (dm, "synthetic-detection")):
        _require(type(meta["schema_version"]) is int and meta["schema_version"] == 1
                 and meta["artifact_type"] == kind and meta["status"] == "complete",
                 "dataset metadata is not complete/schema-1")
        _require(meta["dataset_id"] == meta["identity_scope"] == dataset_id
                 and meta["split"] == split, "dataset identity mismatch")
    months = _months(gm["observed_months"])
    _require(dm["observed_months"] == recipe["months"] == months, "dataset month mismatch")
    scenario, seed = gm["scenario"], gm["generator_seed"]
    _require(scenario in SCENARIOS and type(seed) is int
             and seed in recipe["generator"]["seeds"][split], "dataset scenario/seed mismatch")
    prefix = "dev" if split == "development" else "eval"
    _require(dataset_id == f"{prefix}-{scenario}-easy-g{seed}" and gm["difficulty"] == "easy",
             "dataset ID does not match configured identity")
    reference = "truth-" + dataset_id
    for key, expected in {"scenario": scenario, "generator_seed": seed,
                          "truth_reference": reference}.items():
        _require(gm[key] == dm[key] == expected, f"dataset {key} mismatch")
    for key in ("split", "scenario", "generator_seed", "difficulty", "dataset_id"):
        _require(record[key] == gm[key], "dataset record mismatch")
    for stage, path in (("generation", f"inputs/source/{dataset_id}/metadata.json"),
                        ("detection", f"inputs/detected/{dataset_id}/metadata.json")):
        _require(record[stage]["status"] == "complete" and record[stage]["metadata"] == path,
                 "dataset stage metadata mismatch")
    _require(record["evaluation"]["status"] == "complete", "dataset evaluation incomplete")
    _check_files(source, gm["files"], {"metadata.json"})
    _check_files(detected, dm["files"], {"metadata.json"})
    expected_source = {f"snapshots/{m}/{n}.csv" for m in months for n in ("R", "nodes")}
    expected_source |= {"truth/membership.csv", "truth/events.csv", "truth/links.csv", "benchmark-config.json"}
    expected_detected = {f"memberships/{m}/membership-seed{s}.csv" for m in months for s in (0, 1, 2)}
    _require(set(gm["files"]) == expected_source and set(dm["files"]) ==
             expected_detected | {"detection.json", "detector-config.json"}, "dataset file schema mismatch")
    _require(_json(source / "benchmark-config.json") == recipe
             and _json(detected / "detector-config.json") == recipe, "dataset recipe mismatch")
    required_source = expected_source - {"truth/membership.csv", "truth/events.csv", "truth/links.csv"}
    required_source.add("metadata.json")
    _require(set(dm["source"]["files"]) == required_source, "detector source inventory mismatch")
    for name, info in dm["source"]["files"].items():
        _require(info["sha256"] == _digest(_path(source, name)), "detector source hash mismatch")
    detector = dm["detector"]
    _require(detector["seeds"] == [0, 1, 2] and detector["canonical_seed"] == 0
             and all(type(s) is int for s in detector["seeds"])
             and type(detector["canonical_seed"]) is int and detector["gamma"] == 1
             and dm["membership_schema_version"] == 1 and dm["scope"] == "detection"
             and detector["config_file"] == "detector-config.json"
             and detector["config_sha256"] == _digest(detected / "detector-config.json"),
             "detector schedule/schema mismatch")
    month_graphs = []
    for m in months:
        hashes = {"R.csv": gm["files"][f"snapshots/{m}/R.csv"]["sha256"]}
        month_graphs.append({"month": m, "files": hashes,
                             "graph_sha256": sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()})
    fingerprint = sha256(json.dumps({"protocol": PROTOCOL, "months": month_graphs}, sort_keys=True).encode()).hexdigest()
    graph_reference = f"{PROTOCOL}:{fingerprint}"
    refs = {str(s): f"{dataset_id}:{graph_reference}:leiden-rb-v2-gamma1-seed{s}" for s in (0, 1, 2)}
    _require(dm["graph_protocol"] == PROTOCOL and dm["graph_reference"] == graph_reference
             and dm["snapshot_cohort_sha256"] == fingerprint and dm["detector_references"] == refs,
             "detector reference/cohort mapping mismatch")
    nodes, endpoints, edges_by_month = {}, {}, {}
    for month in months:
        rows = _table(source / f"snapshots/{month}/nodes.csv", "month,user_id")
        nodes[month] = {u for m, u in rows}
        _require(len(nodes[month]) == len(rows) and all(m == month for m, u in rows),
                 "duplicate node key or wrong node month")
        edges = _table(source / f"snapshots/{month}/R.csv", "month,source_user_id,target_user_id,weight")
        pairs = set()
        endpoints[month] = set()
        for m, a, b, w in edges:
            weight = float(w)
            _require(m == month and a < b and {a, b} <= nodes[month]
                     and isfinite(weight) and weight == 1 and (a, b) not in pairs, "invalid graph edge")
            pairs.add((a, b))
            endpoints[month].update((a, b))
        edges_by_month[month] = len(edges)
    truth = _members(source / "truth/membership.csv", reference, nodes)
    event_count, link_count = _transitions(source, reference, months, truth)
    counts = {"nodes_by_month": {m: len(nodes[m]) for m in months},
              "edges_by_month": edges_by_month,
              "communities_by_month": {m: len(set(truth[m].values())) for m in months},
              "isolates_by_month": {m: len(nodes[m] - endpoints[m]) for m in months},
              "memberships": sum(map(len, truth.values())), "events": event_count, "links": link_count}
    _require(gm["counts"] == counts, "graph/truth counts mismatch")
    entries = dm["memberships"]
    _require(len(entries) == 6 and {(e["month"], e["seed"]) for e in entries} ==
             {(m, s) for m in months for s in (0, 1, 2)}, "membership mapping keys mismatch")
    snapshots = []
    for entry in sorted(entries, key=lambda e: (e["month"], e["seed"])):
        month, ds = entry["month"], entry["seed"]
        name = f"memberships/{month}/membership-seed{ds}.csv"
        graph, nodefile = f"snapshots/{month}/R.csv", f"snapshots/{month}/nodes.csv"
        _require(type(ds) is int and entry["canonical"] is (ds == 0)
                 and entry["path"] == name and entry["sha256"] == dm["files"][name]["sha256"]
                 and entry["reference_id"] == refs[str(ds)] and entry["dataset_id"] == dataset_id
                 and entry["identity_scope"] == dataset_id and entry["graph_file"] == graph
                 and entry["graph_sha256"] == next(g["graph_sha256"] for g in month_graphs if g["month"] == month)
                 and entry["nodes_file"] == nodefile and entry["active_nodes"] == len(nodes[month])
                 and entry["assigned_users"] == len(endpoints[month])
                 and entry["isolates"] == len(nodes[month] - endpoints[month])
                 and entry["status"] == ("complete" if endpoints[month] else "empty_graph_no_partition"),
                 "membership mapping/counts mismatch")
        predicted = _members(detected / name, refs[str(ds)], {month: endpoints[month]})[month]
        snapshots.append(dict(zip(SNAPSHOT_COLUMNS, [
            dataset_id, split, scenario, seed, month, ds, ds == 0, reference, refs[str(ds)],
            f"inputs/source/{dataset_id}/{nodefile}", f"inputs/source/{dataset_id}/{graph}",
            f"inputs/source/{dataset_id}/truth/membership.csv", f"inputs/source/{dataset_id}/truth/events.csv",
            f"inputs/source/{dataset_id}/truth/links.csv", f"inputs/detected/{dataset_id}/{name}",
            len(nodes[month]), len(endpoints[month]), len(nodes[month] - endpoints[month]),
            len(set(truth[month].values())), len(set(predicted.values()))])))
    return snapshots


def inspect_synthetic_handoff(run_directory: Path, *, expected_manifest_sha256: str | None = None) -> dict:
    """Verify a complete schema-2 run and return a deterministic relative inventory.

    Optional SHA-256 must come from a trusted reference; hashes alone establish
    integrity, not authorship. Source files are checked again before returning.
    Absolute producer paths and the current runtime's freeze gate are not used.
    """
    root = Path(run_directory).resolve()
    manifest_path = root / "manifest.json"
    digest = _digest(manifest_path)
    if expected_manifest_sha256 is not None:
        _require(isinstance(expected_manifest_sha256, str)
                 and re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256)
                 and digest == expected_manifest_sha256, "source manifest SHA-256 mismatch")
    manifest = _json(manifest_path)
    _require(not any((root / n).exists() for n in ("failure.json", "manifest.pending.json")),
             "incomplete/failure marker present")
    _require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 2
             and manifest["status"] == "complete", "run must be complete/schema-2")
    split = manifest["split"]
    types = {"development": ("synthetic-detection-evaluation-run", "development-detection-evaluation"),
             "evaluation": ("synthetic-frozen-evaluation-run", "heldout-detection-evaluation")}
    _require(split in types and (manifest["artifact_type"], manifest["scope"]) == types[split]
             and manifest["tracking_status"] == "not_implemented", "unsupported run scope")
    _require(manifest["completed_stages"] == ["generation", "truth", "detection", "evaluation"]
             and manifest["current_stage"] is None and manifest["current_dataset"] is None
             and set(manifest["stages"]) == {"configuration", "generation", "detection", "evaluation"}
             and all(s["status"] == "complete" for s in manifest["stages"].values()),
             "run stages incomplete")
    files = _check_files(root, manifest["files"], {"manifest.json"}, sizes=True)
    _require(manifest["integrity"]["status"] == "verified" and manifest["integrity"]["source_unchanged"] is True
             and manifest["integrity"]["output_files"] == len(files), "run integrity incomplete")
    for info in manifest["config_inputs"].values():
        _require(files[info["archive"]]["sha256"] == info["sha256"], "config input binding mismatch")
    recipe = _json(_path(root, manifest["config_inputs"]["benchmark"]["archive"]))
    _require(recipe["protocol"] == PROTOCOL and recipe["detector"]["seeds"] == [0, 1, 2]
             and recipe["detector"]["canonical_seed"] == 0 and recipe["detector"]["gamma"] == 1
             and recipe["scenarios"] == list(SCENARIOS), "unsupported recipe/detector policy")
    seeds = recipe["generator"]["seeds"]
    for values in (seeds["development"], seeds["evaluation"]):
        _require(isinstance(values, list) and values and all(type(s) is int and 0 <= s < 2**32 for s in values)
                 and len(set(values)) == len(values), "invalid generator seed schedule")
    _require(not set(seeds["development"]) & set(seeds["evaluation"]), "generator split overlap")
    ids = manifest["selection"]["dataset_ids"]
    _require(isinstance(ids, list) and ids and len(ids) == len(set(ids))
             and all(isinstance(i, str) and re.fullmatch(r"(?:dev|eval)-[a-z]+-easy-g\d+", i) for i in ids),
             "invalid/duplicate dataset IDs")
    mode = manifest["selection"]["mode"]
    _require(mode in (("full-development", "development-subset") if split == "development" else ("full-evaluation",)),
             "unsupported run selection")
    if mode.startswith("full-"):
        prefix = "dev" if split == "development" else "eval"
        scheduled = {f"{prefix}-{case}-easy-g{s}" for case in SCENARIOS for s in seeds[split]}
        _require(set(ids) == scheduled, "full run dataset schedule mismatch")
    _require(set(manifest["dataset_records"]) == set(ids), "dataset records mismatch")
    for kind in ("source", "detected"):
        parent = root / "inputs" / kind
        _require(parent.is_dir() and {p.name for p in parent.iterdir()} == set(ids),
                 "dataset directory inventory mismatch")
    rows = []
    for dataset_id in sorted(ids):
        rows.extend(_dataset(root, dataset_id, recipe, split, manifest["dataset_records"][dataset_id]))
    counts = {"datasets": len(ids), "snapshots": len(rows) // 3, "snapshot_detector_runs": len(rows)}
    _require(manifest["actual_counts"] == manifest["expected_counts"] == counts, "run counts mismatch")
    _require(manifest["progress_counts"] == {k + "_datasets": len(ids)
             for k in ("generated", "detected", "evaluated")}, "run progress mismatch")
    _require(manifest["evaluation_directory"] == "evaluation", "evaluation directory mismatch")
    report = _json(root / "evaluation/metadata.json")
    _require(report["status"] == "complete" and report["schema_version"] == 1
             and report["artifact_type"] == "synthetic-detection-evaluation"
             and report["scope"] == "detection-evaluation-only" and report["dataset_count"] == len(ids)
             and report["metric_rows"] == len(rows), "evaluation report metadata mismatch")
    _check_files(root / "evaluation", report["files"], {"metadata.json"})
    _require(_inventory(root, {"manifest.json"}) == files and _digest(manifest_path) == digest,
             "source changed during inspection")
    return {"schema_version": 1, "artifact_type": "synthetic-handoff-inventory",
            "status": "verified_by_automated_consumer", "partner_acceptance": "not_verified",
            "tracking_status": "not_implemented", "source_manifest_sha256": digest,
            "source_scope": manifest["scope"], "split": split, "dataset_ids": sorted(ids),
            "counts": counts, "canonical_seed": 0, "snapshot_memberships": rows,
            "files": {"manifest.json": {"sha256": digest, "bytes": manifest_path.stat().st_size}, **files},
            "checks": ["complete run", "exact file inventory/hashes/sizes", "dataset identity/source linkage",
                       "truth membership/events/links keys", "all detector seeds/references/endpoint coverage"],
            "not_checked": ["AMI recomputation", "frozen runtime certification", "tracker", "recipient review"]}


def export_synthetic_handoff(run_directory: Path, output: Path, *, expected_manifest_sha256=None) -> dict:
    """Write inventory.json and snapshot CSV in a new directory, metadata last.

    Does not copy the source bundle. A recipient needs both the complete source
    run and this inventory. Failed publication leaves partial files for audit.
    """
    root, output = Path(run_directory).resolve(), Path(output).resolve()
    _require(not output.exists(), "handoff output already exists")
    _require(not output.is_relative_to(root) and not root.is_relative_to(output),
             "handoff output overlaps source")
    inventory = inspect_synthetic_handoff(root, expected_manifest_sha256=expected_manifest_sha256)
    output.mkdir()
    def write_json(path, value):
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
    write_json(output / "inventory.json", inventory)
    with (output / "snapshot_inventory.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(inventory["snapshot_memberships"])
    _require(_inventory(root, set()) == inventory["files"], "source changed before publication")
    metadata = {"schema_version": 1, "artifact_type": "synthetic-handoff-index", "status": "complete",
                "source_manifest_sha256": inventory["source_manifest_sha256"], "counts": inventory["counts"],
                "split": inventory["split"], "partner_acceptance": "not_verified",
                "source_bundle_included": False, "files": _inventory(output, {"metadata.json"})}
    write_json(output / "metadata.json", metadata)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = export_synthetic_handoff(args.run_directory, args.output,
                                         expected_manifest_sha256=args.expected_manifest_sha256)
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, csv.Error) as exc:
        print(f"synthetic handoff verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
