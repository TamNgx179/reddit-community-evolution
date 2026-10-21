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
        prog="reddit-sna", description="Reddit SNA: three independent week-one baselines available; HeTCo and proposed research methods remain planned."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("pipelines", help="List independent pipelines and implementation status")
    synthetic = subparsers.add_parser("synthetic-week1", help="Rebuild synthetic graphs, detection, tracking and evaluation without a legacy ZIP")
    synthetic.add_argument("--config", type=Path, required=True)
    synthetic.add_argument("--run-id", required=True)
    demo = subparsers.add_parser("week1", help="Run the core-pair raw/replay to verified forecast and figures")
    demo.add_argument("--config", type=Path, required=True)
    demo.add_argument("--run-id", required=True)
    demo.add_argument("--graph-run", type=Path)
    demo.add_argument("--detection-run", type=Path)
    demo.add_argument("--start", default="2015-01")
    demo.add_argument("--end", default="2016-01")
    demo.add_argument("--test-start", default="2015-10")
    demo.add_argument("--corpus", action="append", help="Explicit subset smoke test, not the all15 result")
    report = subparsers.add_parser("forecast-report", help="Export verified forecast tables and six figure families")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--artifact-root", type=Path, default=Path("artifacts"))
    review = subparsers.add_parser("review-labels", help="Prepare blinded local annotation evidence; does not annotate")
    for flag in ("forecast-run", "graph-run", "detection-run", "output"):
        review.add_argument("--" + flag, type=Path, required=True)
    review.add_argument("--artifact-root", type=Path, default=Path("artifacts"))
    review.add_argument("--per-stratum", type=int, default=5)
    review.add_argument("--seed", type=int, default=42)
    forecast_parser = subparsers.add_parser("forecast", help="Track verified memberships and evaluate temporal baselines")
    forecast_parser.add_argument("--graph-run", type=Path, required=True)
    forecast_parser.add_argument("--detection-run", type=Path, required=True)
    forecast_parser.add_argument("--artifact-root", type=Path, default=Path("artifacts"))
    forecast_parser.add_argument("--output", type=Path, required=True)
    forecast_parser.add_argument("--test-start", required=True, help="First held-out label month, YYYY-MM")
    forecast_parser.add_argument("--threshold", type=float, default=0.25)
    forecast_parser.add_argument("--seed", type=int, default=42)
    forecast_parser.add_argument("--tracker", choices=("jaccard", "ged"), default="jaccard")
    forecast_parser.add_argument("--alpha", type=float, default=0.5)
    forecast_parser.add_argument("--beta", type=float, default=0.5)
    forecast_parser.add_argument("--dissolve", type=float, default=0.1)
    forecast_parser.add_argument("--history", action="store_true", help="Add past-only lineage features")
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
            status = {
                PipelineName.CORE: "prepare/forecast/week1 implemented; generic run remains planned",
                PipelineName.DETECTION_TRACKING: "generation/detection/tracking/synthetic-week1 implemented; generic run remains planned",
                PipelineName.PREDICTION: "table/split/baselines/evaluation implemented",
            }[pipeline]
            print(f"{pipeline.value}: {status} ({description})")
        return 0
    try:
        if args.command == "synthetic-week1":
            from reddit_sna.pipelines.synthetic_week1 import run_demo
            print(json.dumps({"synthetic_week1_output": str(run_demo(args.config, args.run_id))}))
            return 0
        if args.command == "week1":
            from reddit_sna.pipelines.week1 import run_demo
            output = run_demo(args.config, args.run_id, graph_run=args.graph_run, detection_run=args.detection_run,
                              start=args.start, end=args.end, test_start=args.test_start, corpora=args.corpus)
            print(json.dumps({"week1_output": str(output)}))
            return 0
        if args.command == "forecast-report":
            from reddit_sna.reporting.forecast import export_report
            print(json.dumps({"report_output": str(export_report(args.run, args.output, args.artifact_root))}))
            return 0
        if args.command == "review-labels":
            from reddit_sna.reporting.label_review import prepare_review
            output = prepare_review(args.forecast_run, args.graph_run, args.detection_run, args.output,
                                    args.artifact_root, per_stratum=args.per_stratum, seed=args.seed)
            print(json.dumps({"review_output": str(output), "annotation_status": "pending"}))
            return 0
        if args.command == "forecast":
            from reddit_sna.pipelines.forecast import run_forecast
            output = run_forecast(args.graph_run, args.detection_run, args.artifact_root,
                                  args.output, args.test_start, args.threshold, args.seed,
                                  tracker=args.tracker, alpha=args.alpha, beta=args.beta,
                                  dissolve=args.dissolve, history=args.history)
            print(json.dumps({"forecast_output": str(output)}))
            return 0
        config = load_config(args.config, run_id=args.run_id)
        if args.command == "prepare":
            from reddit_sna.data.archive import CORPORA
            from reddit_sna.pipelines.preparation import run_preparation
            output = run_preparation(config, stage=args.stage, start=args.start, end=args.end,
                             corpora=tuple(args.corpus) if args.corpus else CORPORA,
                             source_run=args.source_run)
            print(json.dumps({"preparation_output": str(output), "forecast_status": "not_run_by_preparation", "next_stage": "forecast or week1"}))
            return 0
        if args.command == "check":
            support = {PipelineName.CORE: "prepare_forecast_week1_available",
                       PipelineName.DETECTION_TRACKING: "synthetic_week1_available",
                       PipelineName.PREDICTION: "prediction_evaluation_available"}[config.pipeline]
            generic = "implemented" if config.pipeline == PipelineName.PREDICTION else "scaffold-only"
            print(json.dumps({"config_status": "valid", "pipeline_status": support, "generic_run_status": generic, **config.to_dict()}, indent=2, ensure_ascii=False))
            return 0
        _run_selected(config)
    except PipelineNotImplemented as exc:
        print(f"Not implemented: {exc}. No evaluation results were created.", file=sys.stderr)
        return 3
    except (ImportError, RuntimeError) as exc:
        print(f"Error: {exc}. Install the required project extras with this interpreter.", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (zipfile.BadZipFile, sqlite3.DatabaseError) as exc:
        print(f"Error: input/store integrity failure ({type(exc).__name__})", file=sys.stderr)
        return 2
    return 0
