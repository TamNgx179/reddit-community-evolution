"""Independent tiny CSV/JSON fixtures; no producer, Leiden or AMI calls."""

import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from reddit_sna.reporting import synthetic_handoff as consumer


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns.split(","))
        writer.writerows(rows)


def files(root, excluded=()):
    return {p.relative_to(root).as_posix(): {"sha256": sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
            for p in sorted(root.rglob("*")) if p.is_file() and p.relative_to(root).as_posix() not in excluded}


class SyntheticHandoffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-handoff-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.run = self.base / "run"
        self.did = "dev-stable-easy-g11"
        self.source = self.run / "inputs/source" / self.did
        self.detected = self.run / "inputs/detected" / self.did
        self.build()

    def build(self, *, no_edges=False, no_nodes=False):
        """A stable three-user contract fixture with one isolate; not a benchmark run."""
        months = ["2020-01", "2020-02"]
        users = [] if no_nodes else ["a", "b", 'người,cô lập "c"']
        assigned = [] if no_nodes or no_edges else users[:2]
        self.source.mkdir(parents=True, exist_ok=True)
        self.detected.mkdir(parents=True, exist_ok=True)
        recipe = {"protocol": consumer.PROTOCOL, "months": months, "scenarios": list(consumer.SCENARIOS),
                  "generator": {"seeds": {"development": [11, 12, 13], "evaluation": [101, 102, 103]}},
                  "detector": {"gamma": 1, "seeds": [0, 1, 2], "canonical_seed": 0}}
        config = self.run / "config/benchmark.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        for p in (config, self.source / "benchmark-config.json", self.detected / "detector-config.json"):
            write_json(p, recipe)
        truthref = "truth-" + self.did
        for month in months:
            write_csv(self.source / f"snapshots/{month}/nodes.csv", "month,user_id", [(month, u) for u in users])
            write_csv(self.source / f"snapshots/{month}/R.csv", "month,source_user_id,target_user_id,weight",
                      [(month, "a", "b", 1.0)] if assigned else [])
        truth = [[truthref, m, "A" if u in ("a", "b") else "K", u] for m in months for u in users]
        write_csv(self.source / "truth/membership.csv", consumer.MEMBERSHIP, truth)
        groups = ["A", "K"] if users else []
        write_csv(self.source / "truth/events.csv", "reference_id,source_month,source_community_id,target_month,event",
                  [[truthref, months[0], g, months[1], "stable"] for g in groups])
        write_csv(self.source / "truth/links.csv", "reference_id,source_month,source_community_id,target_month,target_community_id",
                  [[truthref, months[0], g, months[1], g] for g in groups])
        common = {"schema_version": 1, "status": "complete", "dataset_id": self.did, "identity_scope": self.did,
                  "scenario": "stable", "generator_seed": 11, "split": "development", "truth_reference": truthref,
                  "observed_months": months}
        counts = {"nodes_by_month": dict.fromkeys(months, len(users)), "edges_by_month": dict.fromkeys(months, int(bool(assigned))),
                  "communities_by_month": dict.fromkeys(months, len(groups)),
                  "isolates_by_month": dict.fromkeys(months, len(users) - len(assigned)),
                  "memberships": len(truth), "events": len(groups), "links": len(groups)}
        write_json(self.source / "metadata.json", {**common, "artifact_type": "synthetic-graph-truth", "difficulty": "easy",
                   "counts": counts, "files": files(self.source, {"metadata.json"})})
        month_graphs = []
        for m in months:
            hashes = {"R.csv": sha256((self.source / f"snapshots/{m}/R.csv").read_bytes()).hexdigest()}
            month_graphs.append({"month": m, "files": hashes,
                                 "graph_sha256": sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()})
        fingerprint = sha256(json.dumps({"protocol": consumer.PROTOCOL, "months": month_graphs}, sort_keys=True).encode()).hexdigest()
        graphref = consumer.PROTOCOL + ":" + fingerprint
        refs = {str(s): f"{self.did}:{graphref}:leiden-rb-v2-gamma1-seed{s}" for s in (0, 1, 2)}
        entries = []
        for m in months:
            for s in (0, 1, 2):
                name = f"memberships/{m}/membership-seed{s}.csv"
                write_csv(self.detected / name, consumer.MEMBERSHIP, [[refs[str(s)], m, "0", u] for u in assigned])
                entries.append({"month": m, "seed": s, "canonical": s == 0, "path": name,
                                "sha256": sha256((self.detected / name).read_bytes()).hexdigest(),
                                "reference_id": refs[str(s)], "dataset_id": self.did, "identity_scope": self.did,
                                "graph_file": f"snapshots/{m}/R.csv", "nodes_file": f"snapshots/{m}/nodes.csv",
                                "graph_sha256": next(g["graph_sha256"] for g in month_graphs if g["month"] == m),
                                "active_nodes": len(users), "assigned_users": len(assigned), "isolates": len(users)-len(assigned),
                                "status": "complete" if assigned else "empty_graph_no_partition"})
        write_json(self.detected / "detection.json", {"fixture_only": True})
        source_files = files(self.source)
        source_files = {k: v for k, v in source_files.items() if not k.startswith("truth/")}
        write_json(self.detected / "metadata.json", {**common, "artifact_type": "synthetic-detection", "scope": "detection",
                   "membership_schema_version": 1, "detector_references": refs, "memberships": entries,
                   "graph_reference": graphref, "graph_protocol": consumer.PROTOCOL, "snapshot_cohort_sha256": fingerprint,
                   "detector": {"seeds": [0, 1, 2], "canonical_seed": 0, "gamma": 1, "config_file": "detector-config.json",
                                "config_sha256": sha256((self.detected / "detector-config.json").read_bytes()).hexdigest()},
                   "source": {"directory": "Z:/producer-path-does-not-exist", "files": source_files},
                   "files": files(self.detected, {"metadata.json"})})
        report = self.run / "evaluation"
        report.mkdir(exist_ok=True)
        # Report values are not scored by this consumer; only metadata and hashes.
        (report / "detection_metrics.csv").write_text("fixture_only\n", encoding="utf-8")
        write_json(report / "metadata.json", {"schema_version": 1, "artifact_type": "synthetic-detection-evaluation",
                   "status": "complete", "scope": "detection-evaluation-only", "dataset_count": 1, "metric_rows": 6,
                   "files": files(report, {"metadata.json"})})
        record = {"dataset_id": self.did, "split": "development", "scenario": "stable", "generator_seed": 11,
                  "difficulty": "easy", "generation": {"status": "complete", "metadata": f"inputs/source/{self.did}/metadata.json"},
                  "detection": {"status": "complete", "metadata": f"inputs/detected/{self.did}/metadata.json"},
                  "evaluation": {"status": "complete"}}
        expected = {"datasets": 1, "snapshots": 2, "snapshot_detector_runs": 6}
        write_json(self.run / "manifest.json", {"schema_version": 2, "status": "complete", "split": "development",
                   "artifact_type": "synthetic-detection-evaluation-run", "scope": "development-detection-evaluation",
                   "tracking_status": "not_implemented", "current_stage": None, "current_dataset": None,
                   "completed_stages": ["generation", "truth", "detection", "evaluation"],
                   "stages": {s: {"status": "complete"} for s in ("configuration", "generation", "detection", "evaluation")},
                   "config_inputs": {"benchmark": {"archive": "config/benchmark.json", "sha256": sha256(config.read_bytes()).hexdigest()}},
                   "selection": {"dataset_ids": [self.did], "mode": "development-subset"},
                   "dataset_records": {self.did: record}, "evaluation_directory": "evaluation",
                   "actual_counts": expected, "expected_counts": expected,
                   "progress_counts": {s + "_datasets": 1 for s in ("generated", "detected", "evaluated")},
                   "integrity": {"status": "verified", "source_unchanged": True,
                                 "output_files": len(files(self.run, {"manifest.json"}))},
                   "files": files(self.run, {"manifest.json"})})

    def inspect(self):
        return consumer.inspect_synthetic_handoff(self.run)

    def reseal(self):
        """Update all nested byte bindings so adversarial tests reach semantics."""
        gm = json.loads((self.source / "metadata.json").read_bytes())
        gm["files"] = files(self.source, {"metadata.json"})
        write_json(self.source / "metadata.json", gm)
        dm = json.loads((self.detected / "metadata.json").read_bytes())
        dm["source"]["files"] = {k: v for k, v in files(self.source).items() if not k.startswith("truth/")}
        dm["files"] = files(self.detected, {"metadata.json"})
        for entry in dm["memberships"]:
            entry["sha256"] = dm["files"][entry["path"]]["sha256"]
        write_json(self.detected / "metadata.json", dm)
        self.root_reseal()

    def root_reseal(self):
        self.edit_json(self.run / "manifest.json", lambda m: m.update(files=files(self.run, {"manifest.json"})))
        self.edit_json(self.run / "manifest.json", lambda m: m["integrity"].update(output_files=len(m["files"])))

    def edit_json(self, path, edit):
        data = json.loads(path.read_bytes())
        edit(data)
        write_json(path, data)

    def membership(self):
        return self.detected / "memberships/2020-01/membership-seed0.csv"

    def edit_table(self, path, edit):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        edit(rows)
        write_csv(path, ",".join(rows[0]), rows[1:])

    def test_isolates_references_canonical_and_recipient_state(self):
        before = files(self.run)
        result = self.inspect()
        self.assertEqual(result["counts"], {"datasets": 1, "snapshots": 2, "snapshot_detector_runs": 6})
        self.assertEqual(result["partner_acceptance"], "not_verified")
        self.assertEqual(sum(r["canonical"] for r in result["snapshot_memberships"]), 2)
        self.assertEqual(result["snapshot_memberships"][0]["isolated_nodes"], 1)
        self.assertEqual(result["snapshot_memberships"][0]["endpoint_nodes"], 2)
        self.assertEqual(files(self.run), before)

    def test_header_only_memberships_with_all_isolates(self):
        self.build(no_edges=True)
        result = self.inspect()
        self.assertTrue(all(r["endpoint_nodes"] == r["predicted_communities"] == 0
                            and r["active_nodes"] == 3 for r in result["snapshot_memberships"]))

    def test_empty_observed_months_remain_explicit(self):
        self.build(no_nodes=True)
        result = self.inspect()
        self.assertEqual(len(result["snapshot_memberships"]), 6)
        self.assertTrue(all(r["active_nodes"] == 0 for r in result["snapshot_memberships"]))

    def test_relocation_and_export_are_deterministic(self):
        moved = self.base / "relocated"
        shutil.copytree(self.run, moved)
        self.assertEqual(self.inspect(), consumer.inspect_synthetic_handoff(moved))
        for name, run in (("first", self.run), ("second", moved)):
            consumer.export_synthetic_handoff(run, self.base / name)
        self.assertEqual(files(self.base / "first"), files(self.base / "second"))

    def test_existing_output_and_overlap_are_rejected_without_writes(self):
        existing = self.base / "existing"
        existing.mkdir()
        for target in (existing, self.run / "child", self.base):
            with self.subTest(target=target), self.assertRaises(ValueError):
                consumer.export_synthetic_handoff(self.run, target)
        self.assertEqual(list(existing.iterdir()), [])
        self.assertFalse((self.run / "child").exists())

    def test_started_failed_and_bool_schema_rejected_before_output(self):
        original = (self.run / "manifest.json").read_bytes()
        for changes in ({"status": "started"}, {"status": "failed"}, {"schema_version": True}):
            with self.subTest(changes=changes):
                (self.run / "manifest.json").write_bytes(original)
                self.edit_json(self.run / "manifest.json", lambda m: m.update(changes))
                with self.assertRaisesRegex(ValueError, "complete/schema-2"):
                    consumer.export_synthetic_handoff(self.run, self.base / "out")
                self.assertFalse((self.base / "out").exists())

    def test_pending_failure_markers_rejected(self):
        for name in ("failure.json", "manifest.pending.json"):
            with self.subTest(name=name):
                marker = self.run / name
                marker.write_text("{}")
                with self.assertRaisesRegex(ValueError, "marker"):
                    self.inspect()
                marker.unlink()

    def test_corrupted_bytes_and_extra_files_rejected(self):
        path = self.membership()
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.inspect()
        (self.run / "extra.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            self.inspect()

    def test_pin_rejects_wrong_or_invalid_digest(self):
        for digest in ("0" * 64, "not-a-hash", True):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "manifest SHA-256"):
                consumer.inspect_synthetic_handoff(self.run, expected_manifest_sha256=digest)

    def test_duplicate_json_keys_rejected(self):
        path = self.run / "manifest.json"
        path.write_text(path.read_text().rstrip()[:-1] + ', "status": "complete"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.inspect()

    def test_resealed_duplicate_predicted_user_rejected(self):
        self.edit_table(self.membership(), lambda rows: rows.append(rows[1]))
        self.reseal()
        with self.assertRaisesRegex(ValueError, "duplicate membership"):
            self.inspect()

    def test_resealed_missing_endpoint_rejected(self):
        self.edit_table(self.membership(), lambda rows: rows.pop())
        self.reseal()
        with self.assertRaisesRegex(ValueError, "endpoint mismatch"):
            self.inspect()

    def test_resealed_unknown_user_rejected(self):
        self.edit_table(self.membership(), lambda rows: rows[1].__setitem__(3, "unknown"))
        self.reseal()
        with self.assertRaisesRegex(ValueError, "endpoint mismatch"):
            self.inspect()

    def test_resealed_wrong_reference_and_month_rejected(self):
        original = self.membership().read_bytes()
        for column in (0, 1):
            with self.subTest(column=column):
                self.membership().write_bytes(original)
                self.edit_table(self.membership(), lambda rows: rows[1].__setitem__(column, "wrong"))
                self.reseal()
                with self.assertRaisesRegex(ValueError, "reference/month"):
                    self.inspect()

    def test_resealed_missing_truth_user_rejected(self):
        self.edit_table(self.source / "truth/membership.csv", lambda rows: rows.pop())
        self.reseal()
        with self.assertRaisesRegex(ValueError, "coverage/endpoint"):
            self.inspect()

    def test_resealed_wrong_csv_header_and_width_rejected(self):
        original = self.membership().read_bytes()
        for modify in (lambda rows: rows[0].__setitem__(0, "wrong"), lambda rows: rows[1].append("extra")):
            self.membership().write_bytes(original)
            self.edit_table(self.membership(), modify)
            self.reseal()
            with self.assertRaisesRegex(ValueError, "CSV schema|invalid CSV row"):
                self.inspect()

    def test_resealed_truth_event_or_link_keys_rejected(self):
        path = self.source / "truth/events.csv"
        self.edit_table(path, lambda rows: rows[1].__setitem__(1, "2020-02"))
        self.reseal()
        with self.assertRaisesRegex(ValueError, "truth event"):
            self.inspect()

    def test_resealed_missing_seed_mapping_rejected(self):
        self.edit_json(self.detected / "metadata.json", lambda m: m["memberships"].pop())
        self.root_reseal()
        with self.assertRaisesRegex(ValueError, "mapping keys"):
            self.inspect()

    def test_resealed_swapped_reference_mapping_rejected(self):
        self.edit_json(self.detected / "metadata.json", lambda m: m["detector_references"].update({"0": "other-dataset:fake"}))
        self.root_reseal()
        with self.assertRaisesRegex(ValueError, "reference/cohort"):
            self.inspect()

    def test_resealed_full_selection_cannot_omit_scheduled_datasets(self):
        self.edit_json(self.run / "manifest.json", lambda m: m["selection"].update(mode="full-development"))
        with self.assertRaisesRegex(ValueError, "full run dataset schedule"):
            self.inspect()

    def test_resealed_source_binding_rejected(self):
        self.edit_json(self.detected / "metadata.json", lambda m: m["source"]["files"]["metadata.json"].update(sha256="0" * 64))
        self.root_reseal()
        with self.assertRaisesRegex(ValueError, "source hash"):
            self.inspect()

    def test_path_traversal_and_symlink_are_rejected(self):
        for name in ("../outside", "/absolute", "C:/absolute", "a\\b", "a/../b"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "path"):
                consumer._path(self.run, name)
        try:
            (self.run / "linked").symlink_to(self.membership())
        except OSError:
            return  # Path rules above run even where Windows disallows symlink creation.
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.inspect()

    def test_source_mutation_during_inspection_rejected(self):
        original = consumer._dataset
        def change(*args):
            rows = original(*args)
            self.membership().write_bytes(self.membership().read_bytes() + b" ")
            return rows
        with patch.object(consumer, "_dataset", side_effect=change), self.assertRaisesRegex(ValueError, "source changed"):
            self.inspect()

    def test_publish_failure_keeps_partial_files_without_complete_metadata(self):
        output = self.base / "partial"
        dump = json.dump
        calls = 0
        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated metadata failure")
            return dump(*args, **kwargs)
        with patch.object(consumer.json, "dump", side_effect=fail_second), self.assertRaisesRegex(OSError, "simulated"):
            consumer.export_synthetic_handoff(self.run, output)
        self.assertTrue((output / "inventory.json").is_file())
        self.assertTrue((output / "snapshot_inventory.csv").is_file())
        self.assertEqual((output / "metadata.json").stat().st_size, 0)
        with self.assertRaisesRegex(ValueError, "already exists"):
            consumer.export_synthetic_handoff(self.run, output)

    def test_standalone_cli_without_site_packages_or_repo_imports(self):
        script = self.base / "consumer.py"
        shutil.copyfile(consumer.__file__, script)
        output = self.base / "cli-output"
        pin = sha256((self.run / "manifest.json").read_bytes()).hexdigest()
        command = [sys.executable, "-I", "-S", str(script), str(self.run), "--output", str(output),
                   "--expected-manifest-sha256", pin]
        result = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["partner_acceptance"], "not_verified")
        retry = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(retry.returncode, 2)
        self.assertEqual(retry.stdout, "")


if __name__ == "__main__":
    unittest.main()
