"""One explicit core-pair demo: raw or verified replay to forecast and figures."""

from dataclasses import replace
import json
from pathlib import Path

from reddit_sna.config import load_config, validate_run_id
from reddit_sna.data.archive import digest_file


def run_demo(config_path: Path, run_id: str, *, graph_run=None, detection_run=None,
             start="2015-01", end="2016-01", test_start="2015-10", corpora=None):
    """Delegate to implemented stages; never silently discover a local cohort.

    Replay requires both inputs explicitly. Raw mode creates a new preparation
    cohort. The new demo directory binds forecast/report manifests and records
    failed status if any stage fails; previous outputs always remain immutable.
    """
    from reddit_sna.pipelines.forecast import run_forecast
    from reddit_sna.pipelines.preparation import run_preparation
    from reddit_sna.reporting.forecast import export_report
    from reddit_sna.reporting.handoff import inspect_handoff

    validate_run_id(run_id)
    config = load_config(config_path, run_id=run_id)
    if config.pipeline.value != "core":
        raise ValueError("Week-one demo requires a core config")
    if (graph_run is None) != (detection_run is None):
        raise ValueError("Replay requires both --graph-run and --detection-run")
    artifact_root = config.project_root / "artifacts"
    output = config.run_directory
    if output.exists():
        raise FileExistsError("Demo output already exists; choose a new run ID")
    # Dependency preflight before expensive raw preparation or output reservation.
    try:
        import sklearn  # noqa: F401 -- intentionally preflight the optional extra
        from reddit_sna.reporting.figures import plotting_dependencies
        plotting_dependencies()
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError('Install demo dependencies: python -m pip install -e ".[graph,forecast,notebook]"') from exc
    if graph_run is not None:
        graph_run, detection_run = Path(graph_run).resolve(), Path(detection_run).resolve()
        inspect_handoff(graph_run, detection_run, artifact_root)
    preparation_id = validate_run_id(run_id + "-input")
    if graph_run is None and replace(config, run_id=preparation_id).run_directory.exists():
        raise FileExistsError("Preparation output already exists")
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(status="started", mode="verified_replay" if graph_run else "raw_rebuild",
                    config_sha256=digest_file(config_path), test_start_label_month=test_start)
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        if graph_run is None:
            arguments = dict(start=start, end=end)
            if corpora is not None:
                arguments["corpora"] = tuple(corpora)
            graph_run = detection_run = run_preparation(replace(config, run_id=preparation_id), **arguments)
        forecast = run_forecast(graph_run, detection_run, artifact_root, output / "forecast",
                                test_start, tracker="ged", history=True)
        report = export_report(forecast, output / "report", artifact_root)
        manifest.update(status="complete", graph_run=str(graph_run), detection_run=str(detection_run),
                        forecast_run=str(forecast), report_run=str(report),
                        stage_manifests={"forecast/manifest.json": digest_file(forecast / "manifest.json"),
                                         "report/manifest.json": digest_file(report / "manifest.json")})
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output
