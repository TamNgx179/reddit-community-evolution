"""Small CLI for selecting and validating independent research pipelines."""

import argparse
import json
from pathlib import Path
import sys

from reddit_sna.config import ConfigError, RunConfig, load_config
from reddit_sna.contracts import PipelineName
from reddit_sna.pipelines import PipelineNotImplemented


def _run_selected(config: RunConfig) -> None:
    if config.pipeline == PipelineName.CORE:
        from reddit_sna.pipelines.core import run
    elif config.pipeline == PipelineName.DETECTION_TRACKING:
        from reddit_sna.pipelines.detection_tracking import run
    else:
        from reddit_sna.pipelines.prediction import run
    run(config)


def main(argv: list[str] | None = None) -> int:
    # Console launchers and redirected Windows streams may default to cp1252.
    # Keep CLI output UTF-8, including Vietnamese owners and filesystem paths.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        prog="reddit-sna", description="Reddit SNA source foundation; research pipelines are not implemented yet."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("pipelines", help="List independent pipelines and implementation status")
    for command, help_text in (
        ("check", "Validate config and paths without creating outputs or running algorithms"),
        ("run", "Run selected pipeline; scaffold-only pipelines fail explicitly"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("--config", type=Path, required=True, help="TOML config; relative paths use its folder")
        subparser.add_argument("--run-id", help="Override the config run ID; existing runs cannot be overwritten")
    args = parser.parse_args(argv)
    if args.command == "pipelines":
        for pipeline, owners in (
            (PipelineName.CORE, "Tâm–Thanh"),
            (PipelineName.DETECTION_TRACKING, "Phúc–Đăng"),
            (PipelineName.PREDICTION, "Trâm–Anh"),
        ):
            print(f"{pipeline.value}: scaffold-only ({owners})")
        return 0
    try:
        config = load_config(args.config, run_id=args.run_id)
        if args.command == "check":
            print(json.dumps({"config_status": "valid", "pipeline_status": "scaffold-only", **config.to_dict()}, indent=2, ensure_ascii=False))
            return 0
        _run_selected(config)
    except PipelineNotImplemented as exc:
        print(f"Not implemented: {exc}. No evaluation results were created.", file=sys.stderr)
        return 3
    except (ConfigError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0
