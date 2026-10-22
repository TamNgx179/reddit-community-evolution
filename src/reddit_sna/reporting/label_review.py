"""Prepare local, blinded annotation evidence; never manufacture human labels."""

from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random

from reddit_sna.data.archive import digest_file
from reddit_sna.reporting.forecast_handoff import read_handoff
from reddit_sna.reporting.handoff import inspect_handoff


def prepare_review(forecast_run: Path, graph_run: Path, detection_run: Path,
                   output: Path, artifact_root: Path, *, per_stratum=5, seed=42):
    """Sample source transitions, with hidden strata and case-local member tokens.

    Strata are operational labels plus explicit unresolved reasons. This is a
    diagnostic sample, not a prevalence estimate. Keep answer_key.json away from
    reviewers; the directory structure is not an access-control mechanism.
    """
    if type(per_stratum) is not int or per_stratum < 1 or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Require positive integer sample size and seed in [0, 2**32)")
    output = output.resolve()
    if not output.is_relative_to(artifact_root.resolve()) or output == artifact_root.resolve():
        raise ValueError("Review output must be a child of artifacts")
    if any(output.is_relative_to(source.resolve()) for source in (forecast_run, graph_run, detection_run)):
        raise ValueError("Review output must not modify its immutable sources")
    if output.exists():
        raise FileExistsError("Review output already exists")
    delivery = read_handoff(forecast_run)
    accepted = inspect_handoff(graph_run, detection_run, artifact_root)
    if set(delivery["manifest"]["source_manifests"].values()) != {
            digest_file(graph_run / "manifest.json"), digest_file(detection_run / "manifest.json")}:
        raise ValueError("Review input manifests differ from the forecast sources")
    if {r["reference_id"] for r in delivery["labels"]} != {accepted["canonical_reference"]}:
        raise ValueError("Review cohort mismatch")
    rng = random.Random(seed)
    strata = defaultdict(list)
    for row in delivery["labels"]:
        strata[row["label"] or row["reason"]].append(row)
    chosen = []
    for name, rows in sorted(strata.items()):
        chosen.extend(rng.sample(sorted(rows, key=lambda r: (r["feature_month"], r["community_id"])), min(per_stratum, len(rows))))
    rng.shuffle(chosen)  # Case ordering does not disclose stratum allocation.
    detection = json.loads((detection_run / "detection.json").read_text(encoding="utf-8"))
    groups = {}
    for month in {r[k] for r in chosen for k in ("feature_month", "label_month")}:
        groups[month] = defaultdict(set)
        with (detection_run / "memberships" / month / f"membership-seed{detection['canonical_seed']}.csv").open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                groups[month][row["community_id"]].add(row["user_id"])
    evidence, key, annotations = [], [], []
    for index, row in enumerate(chosen):
        case_id = f"case-{index + 1:04d}"
        source = groups[row["feature_month"]][row["community_id"]]
        target = {cid: users for cid, users in groups[row["label_month"]].items() if source & users}
        target_users = set().union(*target.values()) if target else set()
        predecessors = {cid: users for cid, users in groups[row["feature_month"]].items()
                        if users & target_users or cid == row["community_id"]}
        # Tokens are linked only within this case. They are still local research
        # evidence, not a guarantee of anonymity or a full social interpretation.
        token = lambda user: hashlib.sha256(f"{case_id}:{user}".encode()).hexdigest()[:20]
        ordered_source = [row["community_id"]] + sorted(set(predecessors) - {row["community_id"]})
        evidence.append(dict(case_id=case_id, feature_month=row["feature_month"], label_month=row["label_month"],
            focal_source="source-0", current_groups={f"source-{i}": sorted(token(u) for u in predecessors[cid]) for i, cid in enumerate(ordered_source)},
            next_overlapping_groups={f"target-{i}": sorted(token(u) for u in target[cid]) for i, cid in enumerate(sorted(target))},
            evidence_scope="Observed reply-network memberships only; all targets overlapping the focal source and their current predecessors. No overlap is not proof of social dissolution."))
        key.append(dict(case_id=case_id, **row))
        for reviewer in ("reviewer_a", "reviewer_b"):
            annotations.append(dict(case_id=case_id, reviewer=reviewer, human_label="", confidence="", rationale=""))
    # Recheck input integrity before publishing evidence prepared in memory.
    read_handoff(forecast_run)
    inspect_handoff(graph_run, detection_run, artifact_root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "reviewer").mkdir()
    (output / "coordinator").mkdir()
    (output / "reviewer/cases.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    with (output / "reviewer/annotations.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case_id", "reviewer", "human_label", "confidence", "rationale"])
        writer.writeheader()
        writer.writerows(annotations)
    (output / "coordinator/answer_key.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    manifest = dict(status="prepared_pending_human_annotation", seed=seed, per_stratum=per_stratum,
                    population_support={k: len(v) for k, v in strata.items()}, sampled_cases=len(evidence),
                    forecast_manifest_sha256=digest_file(forecast_run / "manifest.json"),
                    label_reference_id=delivery["manifest"]["label_reference_id"],
                    warnings=["Do not give coordinator directory or this stratum manifest to reviewers.",
                              "A stratified convenience sample does not estimate population prevalence.",
                              "Membership evidence supports structural-event review, not social ground truth."],
                    artifact_hashes={p.relative_to(output).as_posix(): digest_file(p) for p in output.rglob("*") if p.is_file()})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output
