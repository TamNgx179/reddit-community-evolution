"""Export development graph/truth datasets for one seed or the full seed schedule."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from reddit_sna.artifacts import create_run_directory
from reddit_sna.benchmarks.config import dataset_schedule, load_benchmark_config
from reddit_sna.benchmarks.io import export_graph_dataset
from reddit_sna.config import RunConfig, load_config
from reddit_sna.contracts import PipelineName


def export_development_graphs(
    config: RunConfig, benchmark: dict, *, all_development_seeds: bool = False,
) -> Path:
    """Reserve a safe run; complete only generation/truth, with no evaluation.

    By default the TOML seed selects one JSON development generator seed.
    The explicit all_development_seeds option selects the full development list.
    A partial failure is recorded and preserved, never retried into old output.
    """
    if config.pipeline != PipelineName.DETECTION_TRACKING or config.input_kind != "synthetic":
        raise ValueError("graph export requires the synthetic detection-tracking namespace")
    if type(config.seed) is not int or not 0 <= config.seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    if type(all_development_seeds) is not bool:
        raise ValueError("all_development_seeds must be bool")
    schedule = dataset_schedule(benchmark, "development")
    if config.seed not in benchmark["generator"]["seeds"]["development"]:
        raise ValueError("TOML seed must belong to JSON development generator seeds")
    selected = [item for item in schedule
                if all_development_seeds or item["generator_seed"] == config.seed]
    run = create_run_directory(config)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(artifact_type="synthetic-graph-truth-run", scope="graph-truth",
                    split="development", completed_stages=[], datasets=[],
                    selection={"mode": "all-development-seeds" if all_development_seeds else "single-development-seed",
                               "generator_seeds": list(benchmark["generator"]["seeds"]["development"])
                               if all_development_seeds else [config.seed]})
    try:
        datasets = run / "datasets"
        datasets.mkdir()
        for item in selected:
            export_graph_dataset(
                datasets / item["dataset_id"], benchmark=benchmark,
                scenario=item["scenario"], generator_seed=item["generator_seed"],
            )
            manifest["datasets"].append(item["dataset_id"])
        manifest.update(
            status="complete", completed_stages=["generation", "truth"],
            files={path.relative_to(run).as_posix(): {"sha256": sha256(path.read_bytes()).hexdigest()}
                   for path in sorted(datasets.rglob("*")) if path.is_file()},
        )
    except Exception as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        # This is the started manifest of our newly reserved run, never an old run.
        with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/graph_benchmark.toml"))
    parser.add_argument("--benchmark-config", type=Path, default=Path("configs/benchmark_week1.json"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--all-development-seeds", action="store_true",
                        help="export every configured development generator seed; never evaluation")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, run_id=args.run_id)
        benchmark = load_benchmark_config(args.benchmark_config)
        run = export_development_graphs(config, benchmark, all_development_seeds=args.all_development_seeds)
    except (OSError, ValueError) as exc:
        print(f"graph export failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"scope": "graph-truth", "status": "complete", "run_directory": str(run)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
