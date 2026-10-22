"""Export the two truth fixtures without running the detection/tracking pipeline."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from reddit_sna.artifacts import create_run_directory
from reddit_sna.benchmarks.io import export_truth_fixture
from reddit_sna.config import RunConfig, load_config
from reddit_sna.contracts import PipelineName, next_month


def export_truth_fixtures(config: RunConfig, *, start_month: str = "2020-01") -> Path:
    """Reserve a new safe run and export stable/grow with a scoped manifest."""
    if config.pipeline != PipelineName.DETECTION_TRACKING or config.input_kind != "synthetic":
        raise ValueError("truth fixtures require the synthetic detection-tracking namespace")
    if type(config.seed) is not int or not 0 <= config.seed < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    next_month(start_month)
    run = create_run_directory(config)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(artifact_type="synthetic-truth-fixtures", scope="truth-fixtures", datasets=[])
    try:
        datasets = run / "datasets"
        datasets.mkdir()
        for scenario in ("stable", "grow"):
            dataset_id = f"dev-{scenario}-easy-g{config.seed}"
            export_truth_fixture(
                datasets / dataset_id, scenario=scenario, dataset_id=dataset_id,
                generator_seed=config.seed, start_month=start_month,
            )
            manifest["datasets"].append(dataset_id)
        manifest.update(
            status="complete", completed_stages=["truth"], start_month=start_month,
            finished_at=datetime.now(timezone.utc).isoformat(),
            files={path.relative_to(run).as_posix(): {"sha256": sha256(path.read_bytes()).hexdigest()}
                   for path in sorted(datasets.rglob("*")) if path.is_file()},
        )
    except Exception as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        # Only this new run's own started manifest is updated; old runs are refused.
        with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/truth_fixtures.toml"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start-month", default="2020-01")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, run_id=args.run_id)
        run = export_truth_fixtures(config, start_month=args.start_month)
    except (OSError, ValueError) as exc:
        print(f"truth fixture export failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"scope": "truth-fixtures", "status": "complete", "run_directory": str(run)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
