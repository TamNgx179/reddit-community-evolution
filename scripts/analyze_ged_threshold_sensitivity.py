import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

from reddit_sna.tracking.ged import passes
from reddit_sna.contracts import Event

DATA = Path.home() / "Downloads/sna-fullstudy-analysis-inputs/phuc_fullstudy_samples"
SNAPSHOTS = (
    Path.home()
    / "Downloads/Phuc_Coverage_Snapshots_AFTER_REVIEW_LOCK_20261103"
    / "02_AFTER_REVIEW_LOCK/full-study"
)
OUT = Path("analysis_outputs_20261119_ged_sensitivity")

CONFIGS = [
    (0.50, 0.10),
    (0.45, 0.10),
    (0.55, 0.10),
    (0.50, 0.05),
    (0.50, 0.15),
]
CLASSES = [e.value for e in Event]
STATUSES = CLASSES + ["unresolved", "censored"]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def old_status(row):
    if row["reason"] == "final_snapshot_censored":
        return "censored"
    return row["label"] if row["label"] else "unresolved"


def load_membership_sizes():
    sizes = {}
    files = sorted(SNAPSHOTS.glob(
        "months/*/memberships/*/membership-seed0.csv"
    ))
    if len(files) != 45:
        raise RuntimeError(
            f"Expected 45 membership files, found {len(files)}"
        )

    for path in files:
        rows = read_csv(path)
        counts = Counter(
            (r["month"], r["community_id"]) for r in rows
        )
        for key, count in counts.items():
            sizes[key] = count

    return sizes


def classify(row, month_pairs, sizes, alpha, beta, dissolve):
    month_key = (row["feature_month"], row["label_month"])
    sid = row["community_id"]
    pairs = month_pairs.get(month_key, [])
    for p in pairs:
        p["_accepted"] = (
            passes(p["_forward"], alpha)
            or passes(p["_backward"], beta)
        )

    candidates = [
        p for p in pairs
        if p["source_community_id"] == sid
        and p["_accepted"]
    ]

    incoming = Counter(
        p["target_community_id"]
        for p in pairs if p["_accepted"]
    )

    if not candidates:
        weak = any(
            p["source_community_id"] == sid
            and passes(
                max(p["_forward"], p["_backward"]), dissolve
            )
            for p in pairs
        )
        if weak:
            return "unresolved", "weak_overlap_unresolved"
        return Event.DISSOLVE.value, "below_dissolve_threshold"

    if len(candidates) > 1 and any(
        incoming[p["target_community_id"]] > 1
        for p in candidates
    ):
        return "unresolved", "many_to_many_unresolved"

    if len(candidates) > 1:
        return Event.SPLIT.value, "multiple_successors"

    target_id = candidates[0]["target_community_id"]
    if incoming[target_id] > 1:
        return Event.MERGE.value, "multiple_predecessors"

    source_size = int(row["size"])
    target_key = (row["label_month"], target_id)
    if target_key not in sizes:
        raise RuntimeError(f"Missing target membership size: {target_key}")

    difference = sizes[target_key] - source_size
    if difference > 0:
        return Event.GROW.value, "one_to_one_size_comparison"
    if difference < 0:
        return Event.SHRINK.value, "one_to_one_size_comparison"
    return Event.STABLE.value, "one_to_one_size_comparison"


def main():
    OUT.mkdir(exist_ok=True)

    labels = read_csv(DATA / "labels.csv")
    pairs = read_csv(DATA / "inclusion_pairs.csv")
    sizes = load_membership_sizes()

    if len(labels) != 11745:
        raise RuntimeError(f"Expected 11745 labels, got {len(labels)}")

    # Verify source sizes against membership files.
    for row in labels:
        key = (row["feature_month"], row["community_id"])
        if key not in sizes:
            raise RuntimeError(f"Missing source membership: {key}")
        if sizes[key] != int(row["size"]):
            raise RuntimeError(
                f"Source size mismatch at {key}: "
                f"labels={row['size']}, membership={sizes[key]}"
            )

    month_pairs = defaultdict(list)
    for p in pairs:
        key = (p["feature_month"], p["label_month"])
        p["_forward"] = float(p["inclusion_forward"])
        p["_backward"] = float(p["inclusion_backward"])
        month_pairs[key].append(p)

    results = []
    changes = []
    transitions = []

    for alpha, dissolve in CONFIGS:
        beta = alpha
        current = []
        mismatches = []

        for row in labels:
            if row["reason"] == "final_snapshot_censored":
                new_label, new_reason = "censored", row["reason"]
            else:
                new_label, new_reason = classify(
                    row, month_pairs, sizes, alpha, beta, dissolve
                )

            eligible = int(new_label in CLASSES)
            previous = old_status(row)

            result = {
                "link_threshold": alpha,
                "dissolve_threshold": dissolve,
                "feature_month": row["feature_month"],
                "community_id": row["community_id"],
                "label_month": row["label_month"],
                "old_label": previous,
                "new_label": new_label,
                "old_reason": row["reason"],
                "new_reason": new_reason,
                "old_eligible": int(row["eligible"]),
                "new_eligible": eligible,
            }
            current.append(result)

            if previous != new_label:
                changes.append(result.copy())
                transitions.append({
                    "link_threshold": alpha,
                    "dissolve_threshold": dissolve,
                    "from_label": previous,
                    "to_label": new_label,
                })

            if alpha == 0.50 and dissolve == 0.10:
                if previous != new_label or row["reason"] != new_reason:
                    mismatches.append(result.copy())
                if int(row["eligible"]) != eligible:
                    mismatches.append(result.copy())

        if alpha == 0.50 and dissolve == 0.10 and mismatches:
            write_csv(
                OUT / "baseline_mismatches.csv",
                mismatches,
                list(mismatches[0].keys()),
            )
            raise RuntimeError(
                f"BASELINE FAILED: {len(mismatches)} mismatches. "
                "Stopped; alternative thresholds were not validated."
            )

        counts = Counter(r["new_label"] for r in current)
        observed = sum(counts[s] for s in STATUSES if s != "censored")
        eligible = sum(counts[s] for s in CLASSES)

        results.append({
            "link_threshold": alpha,
            "alpha": alpha,
            "beta": beta,
            "dissolve_threshold": dissolve,
            "total_rows": len(current),
            "observed_denominator": observed,
            "eligible": eligible,
            "unresolved": counts["unresolved"],
            "censored": counts["censored"],
            "changed_labels": sum(
                r["old_label"] != r["new_label"] for r in current
            ),
            "eligibility_changed": sum(
                r["old_eligible"] != r["new_eligible"] for r in current
            ),
            "coverage": eligible / observed if observed else 0,
            **{name: counts[name] for name in STATUSES},
        })

        if alpha == 0.50 and dissolve == 0.10:
            print("BASELINE: EXACT MATCH")
            print(f"Rows: {len(current)}")
            print(f"Observed: {observed}; eligible: {eligible}")
            print(f"Coverage: {eligible / observed:.8%}")

    write_csv(
        OUT / "ged_threshold_sensitivity_reproduced.csv",
        results, list(results[0].keys())
    )

    write_csv(
        OUT / "ged_threshold_case_changes_reproduced.csv",
        changes,
        [
            "link_threshold", "dissolve_threshold",
            "feature_month", "community_id", "label_month",
            "old_label", "new_label", "old_reason", "new_reason",
            "old_eligible", "new_eligible",
        ],
    )

    transition_counts = Counter(
        (
            t["link_threshold"], t["dissolve_threshold"],
            t["from_label"], t["to_label"]
        )
        for t in transitions
    )
    transition_rows = [
        {
            "link_threshold": k[0],
            "dissolve_threshold": k[1],
            "from_label": k[2],
            "to_label": k[3],
            "count": v,
        }
        for k, v in sorted(transition_counts.items())
    ]
    write_csv(
        OUT / "ged_threshold_transitions_reproduced.csv",
        transition_rows,
        [
            "link_threshold", "dissolve_threshold",
            "from_label", "to_label", "count",
        ],
    )

    print("\nALL CONFIGURATIONS COMPLETED")
    print(f"Output directory: {OUT.resolve()}")
    print(f"Summary rows: {len(results)}")
    print(f"Changed-case rows: {len(changes)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)

