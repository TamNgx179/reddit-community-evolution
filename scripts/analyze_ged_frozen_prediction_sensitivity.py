import csv
import sys
from pathlib import Path
from collections import defaultdict
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reddit_sna.evaluation.research import score, KEY, EVENTS

PREDICTIONS = ROOT / "artifacts/acceptance/lan-week4-input-001/full-study-2016/artifacts/temporal/activity-study-001/stages/evaluation/attempt-001/predictions.csv"
CHANGES = ROOT / "analysis_outputs_20261119_ged_sensitivity/ged_threshold_case_changes_reproduced.csv"
OUTPUT = ROOT / "analysis_outputs_20261119_ged_sensitivity"

MODELS = ("hier_lr_dynamic", "hier_hgb_dynamic")
EXPECTED_SEEDS = (42, 43, 44)
CASE_KEY = ("feature_month", "community_id", "label_month")


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def f1(rows):
    return score(rows)["macro_f1_six"]


def main():
    predictions = read_csv(PREDICTIONS)
    changes = read_csv(CHANGES)

    # Load only the two frozen models under study.
    units = defaultdict(dict)
    truths = {}

    for row in predictions:
        if row["model"] not in MODELS:
            continue

        seed = int(row["seed"])
        if seed not in EXPECTED_SEEDS:
            raise ValueError(f"Unexpected seed: {seed}")

        key = tuple(row[field] for field in KEY)
        unit = (row["model"], seed)

        if key in units[unit]:
            raise ValueError(f"Duplicate prediction: {unit}, {key}")

        if row["y_true"] not in EVENTS or row["y_pred"] not in EVENTS:
            raise ValueError(f"Invalid event label: {row}")

        row["seed"] = seed
        row["fallback"] = int(row["fallback"])
        units[unit][key] = row

        if key in truths and truths[key] != row["y_true"]:
            raise ValueError(f"Truth differs across models/seeds: {key}")
        truths[key] = row["y_true"]

    expected_units = {
        (model, seed)
        for model in MODELS
        for seed in EXPECTED_SEEDS
    }
    if set(units) != expected_units:
        raise ValueError(f"Missing model/seed units: {set(units) ^ expected_units}")

    baseline_keys = set(units[(MODELS[0], EXPECTED_SEEDS[0])])
    if len(baseline_keys) != 1269:
        raise ValueError(f"Expected 1269 frozen cases, got {len(baseline_keys)}")

    for unit, rows in units.items():
        if set(rows) != baseline_keys:
            raise ValueError(f"Unequal frozen case keys in {unit}")

    # Change file uses the three fields available in its schema.
    changes_by_config = defaultdict(dict)
    configs = {(0.50, 0.10)}

    for row in changes:
        link = float(row["link_threshold"])
        dissolve = float(row["dissolve_threshold"])
        config = (link, dissolve)
        configs.add(config)

        key = tuple(row[field] for field in CASE_KEY)
        if key in changes_by_config[config]:
            raise ValueError(f"Duplicate changed case: {config}, {key}")

        changes_by_config[config][key] = row

    expected_configs = {
        (0.50, 0.10),
        (0.45, 0.10),
        (0.55, 0.10),
        (0.50, 0.05),
        (0.50, 0.15),
    }
    if configs != expected_configs:
        raise ValueError(f"Unexpected configurations: {configs}")

    detail = []

    for link, dissolve in sorted(configs):
        config = (link, dissolve)
        changed = changes_by_config[config]

        for model in MODELS:
            for seed in EXPECTED_SEEDS:
                original_rows = list(units[(model, seed)].values())

                common_original = []
                common_alternative = []
                removed = 0
                changed_label_keys = set()

                for row in original_rows:
                    key3 = tuple(row[field] for field in CASE_KEY)
                    change = changed.get(key3)

                    original_label = row["y_true"]
                    alternative_label = original_label

                    if change:
                        if change["old_label"] != original_label:
                            raise ValueError(
                                f"Old label mismatch: {key3}; "
                                f"prediction={original_label}, "
                                f"change file={change['old_label']}"
                            )

                        if int(change["old_eligible"]) != 1:
                            raise ValueError(
                                f"Frozen case was not baseline eligible: {key3}"
                            )

                        if int(change["new_eligible"]) == 0:
                            removed += 1
                            continue

                        alternative_label = change["new_label"]

                    if alternative_label not in EVENTS:
                        raise ValueError(
                            f"Alternative label is not a six-class event: "
                            f"{key3}: {alternative_label}"
                        )

                    original_copy = dict(row)
                    original_copy["y_true"] = original_label
                    common_original.append(original_copy)

                    alternative_copy = dict(row)
                    alternative_copy["y_true"] = alternative_label
                    common_alternative.append(alternative_copy)

                    if alternative_label != original_label:
                        changed_label_keys.add(key3)

                if len(common_original) + removed != len(original_rows):
                    raise AssertionError("Case accounting does not balance")

                original_f1 = f1(original_rows)
                common_original_f1 = f1(common_original)
                alternative_f1 = f1(common_alternative)

                detail.append({
                    "link_threshold": link,
                    "dissolve_threshold": dissolve,
                    "model": model,
                    "seed": seed,
                    "original_n": len(original_rows),
                    "common_n": len(common_original),
                    "removed_n": removed,
                    "changed_label_in_common": len(changed_label_keys),
                    "original_f1": original_f1,
                    "original_labels_common_f1": common_original_f1,
                    "alternative_labels_common_f1": alternative_f1,
                    "selection_delta": common_original_f1 - original_f1,
                    "label_delta": alternative_f1 - common_original_f1,
                })

    summary = []
    for link, dissolve in sorted(configs):
        for model in MODELS:
            rows = [
                row for row in detail
                if row["link_threshold"] == link
                and row["dissolve_threshold"] == dissolve
                and row["model"] == model
            ]

            for field in ("original_n", "common_n", "removed_n",
                          "changed_label_in_common"):
                if len({row[field] for row in rows}) != 1:
                    raise ValueError(f"Inconsistent {field} across seeds")

            summary.append({
                "link_threshold": link,
                "dissolve_threshold": dissolve,
                "model": model,
                "original_n": rows[0]["original_n"],
                "common_n": rows[0]["common_n"],
                "removed_n": rows[0]["removed_n"],
                "changed_label_in_common": rows[0]["changed_label_in_common"],
                "original_f1": mean(row["original_f1"] for row in rows),
                "original_labels_common_f1": mean(
                    row["original_labels_common_f1"] for row in rows
                ),
                "alternative_labels_common_f1": mean(
                    row["alternative_labels_common_f1"] for row in rows
                ),
                "selection_delta": mean(row["selection_delta"] for row in rows),
                "label_delta": mean(row["label_delta"] for row in rows),
            })

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "ged_frozen_prediction_sensitivity_reproduced.csv", summary)
    write_csv(OUTPUT / "ged_frozen_prediction_sensitivity_per_seed.csv", detail)

    print("FROZEN PREDICTION SENSITIVITY COMPLETED")
    print(f"Models: {', '.join(MODELS)}")
    print(f"Seeds: {EXPECTED_SEEDS}")
    print(f"Baseline frozen cases: {len(baseline_keys)}")
    print(f"Summary rows: {len(summary)}")
    print(f"Per-seed rows: {len(detail)}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
