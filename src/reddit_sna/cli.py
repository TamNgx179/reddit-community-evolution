"""Small CLI for selecting and validating independent research pipelines."""

import argparse
import json
from pathlib import Path
import sys
import sqlite3
import zipfile

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
    # Keep CLI output UTF-8, including Unicode filesystem paths.
    """Dispatch validation or an implemented stage; return 0 on success, 2 on input errors, 3 for unfinished pipelines."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        prog="reddit-sna", description="Reddit SNA: Reddit raw-to-membership stages available; full forecasting not implemented."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("pipelines", help="List independent pipelines and implementation status")
    preparation_parser = subparsers.add_parser("prepare", help="Prepare Reddit data, reply graphs and memberships; not full core forecasting")
    preparation_parser.add_argument("--config", type=Path, required=True)
    preparation_parser.add_argument("--run-id")
    preparation_parser.add_argument("--stage", choices=("audit", "normalize", "snapshots", "detect", "all"), default="all")
    preparation_parser.add_argument("--start", help="Inclusive train month; default source interval or 2015-01")
    preparation_parser.add_argument("--end", help="Exclusive train month; default source interval or 2015-04")
    preparation_parser.add_argument("--corpus", action="append", help="Explicit corpus subset; default all 15")
    preparation_parser.add_argument("--source-run", type=Path, help="Completed source run for snapshots/detect")
    for command, help_text in (
        ("check", "Validate config and paths without creating outputs or running algorithms"),
        ("run", "Run selected pipeline; scaffold-only pipelines fail explicitly"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("--config", type=Path, required=True, help="TOML config; relative paths use its folder")
        subparser.add_argument("--run-id", help="Override the config run ID; existing runs cannot be overwritten")
    args = parser.parse_args(argv)
    if args.command == "pipelines":
        for pipeline, description in (
            (PipelineName.CORE, "Reddit data"),
            (PipelineName.DETECTION_TRACKING, "Synthetic graphs"),
            (PipelineName.PREDICTION, "Forecasting table"),
        ):
            print(f"{pipeline.value}: scaffold-only ({description})")
        return 0
    try:
        config = load_config(args.config, run_id=args.run_id)
        if args.command == "prepare":
            from reddit_sna.data.archive import CORPORA
            from reddit_sna.pipelines.preparation import run_preparation
            output = run_preparation(config, stage=args.stage, start=args.start, end=args.end,
                             corpora=tuple(args.corpus) if args.corpus else CORPORA,
                             source_run=args.source_run)
            print(json.dumps({"preparation_output": str(output), "forecast_status": "not_implemented"}))
            return 0
        if args.command == "check":
            print(json.dumps({"config_status": "valid", "pipeline_status": "scaffold-only", **config.to_dict()}, indent=2, ensure_ascii=False))
            return 0
        _run_selected(config)
    except PipelineNotImplemented as exc:
        print(f"Not implemented: {exc}. No evaluation results were created.", file=sys.stderr)
        return 3
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (zipfile.BadZipFile, sqlite3.DatabaseError) as exc:
        print(f"Error: input/store integrity failure ({type(exc).__name__})", file=sys.stderr)
        return 2
    return 0
