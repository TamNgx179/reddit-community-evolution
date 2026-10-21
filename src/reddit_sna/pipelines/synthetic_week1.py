"""Rebuild the complete synthetic pair demo without a workstation-only ZIP."""

from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
from time import perf_counter

from reddit_sna.config import load_config, validate_destination
from reddit_sna.contracts import PipelineName


def _digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _evaluation_driver(project):
    """Load the versioned external driver, which archives its own implementation.

    The driver is deliberately outside the frozen package. Loading its explicit
    repository path also works with a regular installed wheel without sys.path edits.
    """
    path = project / "scripts/run_frozen_evaluation.py"
    if not path.is_file():
        raise ValueError("The repository checkout must include scripts/run_frozen_evaluation.py")
    spec = importlib.util.spec_from_file_location("synthetic_evaluation_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_frozen_evaluation


def run_demo(config_path, run_id):
    """Generate both fixed splits, freeze before local evaluation, track and plot.

    These recipes have already been inspected. A chronological local freeze is
    engineering provenance, never a claim that the evaluation is scientifically unseen.
    Every invocation uses a separate workspace so previous completed evaluations
    cannot be hidden or mislabeled as a first historical freeze.
    """
    from reddit_sna.benchmarks.freeze import create_benchmark_freeze
    from reddit_sna.detection.leiden import dependencies
    from reddit_sna.pipelines.detection_tracking import run_synthetic_benchmark
    from reddit_sna.reporting.synthetic_handoff import inspect_synthetic_handoff
    from reddit_sna.reporting.synthetic_demo import load_synthetic_demo, build_synthetic_figures, export_synthetic_demo
    from reddit_sna.reporting.synthetic_cases import analyze_synthetic_cases, build_case_figures, export_case_analysis
    from reddit_sna.reporting.tracking_outputs import run_current_split
    from reddit_sna.reporting.tracking_demo import load_tracking_demo, build_tracking_figures, export_tracking_demo

    config = load_config(Path(config_path), run_id=run_id)
    if config.pipeline != PipelineName.DETECTION_TRACKING or config.seed != 0:
        raise ValueError("Synthetic week-one demo requires a detection-tracking config with seed 0")
    output = validate_destination(config)
    dependencies()
    try:
        import sklearn  # noqa: F401 -- preflight before reserving any output
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError('Install the project extras: .[graph,evaluation,notebook]') from exc
    evaluate = _evaluation_driver(config.project_root)
    recipe_root = config.project_root / "configs"
    for name in ("benchmark_week1.json", "benchmark_week1_protocol.json"):
        if not (recipe_root / name).is_file():
            raise ValueError(f"Missing versioned benchmark input: {name}")
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    manifest = dict(status="started", artifact_type="synthetic-week1-demo",
                    interpretation="Current descriptive rerun of inspected recipes, not a new unseen test",
                    partner_acceptance="not_verified", historical_dang_freeze="not_verified")
    path = output / "manifest.json"
    _save(path, manifest)
    figures = {}
    try:
        workspace = output / "workspace"
        configs = workspace / "configs"
        configs.mkdir(parents=True)
        for name in ("benchmark_week1.json", "benchmark_week1_protocol.json"):
            shutil.copy2(recipe_root / name, configs / name)
        # All stages use the same TOML bytes, source and dependency versions.
        config_file = configs / "run.toml"
        config_file.write_text('schema_version = 1\npipeline = "detection-tracking"\nproject_root = ".."\nseed = 0\n'
                               '[input]\nkind = "synthetic"\n[output]\nroot = "../artifacts"\nrun_id = "development"\n', encoding="utf-8")
        stage = load_config(config_file)
        protocol = configs / "benchmark_week1_protocol.json"
        development = run_synthetic_benchmark(stage, protocol=protocol)
        freeze = create_benchmark_freeze(replace(stage, run_id="freeze"), development_run=development, protocol=protocol)
        evaluation = evaluate(replace(stage, run_id="evaluation"), freeze=freeze)
        runs = {"development": development, "evaluation": evaluation}
        pins = {split: _digest(run / "manifest.json") for split, run in runs.items()}
        bundle = output / "bundle"
        for split, source in runs.items():
            inspect_synthetic_handoff(source, expected_manifest_sha256=pins[split])
            shutil.copytree(source, bundle / "runs" / split)
        delivery = dict(schema_version=1, artifact_type="phuc-dang-synthetic-data-handoff", status="complete",
                        scope=manifest["interpretation"], source_manifest_sha256=pins,
                        files={p.relative_to(bundle).as_posix(): {"sha256": _digest(p), "bytes": p.stat().st_size}
                               for p in sorted(bundle.rglob("*")) if p.is_file()})
        _save(bundle / "delivery-manifest.json", delivery)
        tracking = {split: run_current_split(source, output / "tracking", run_id=split, split=split,
                                             source_manifest_sha256=pins[split]) for split, source in runs.items()}
        reference = dict(mode="current_source", delivery_manifest_sha256=_digest(bundle / "delivery-manifest.json"),
                         source_manifest_sha256=pins, bundle=str(bundle), tracking={s: str(p) for s, p in tracking.items()},
                         interpretation=manifest["interpretation"])
        _save(output / "pair-reference.json", reference)
        demo = load_synthetic_demo(bundle, expected_delivery_sha256=reference["delivery_manifest_sha256"])
        figures.update(build_synthetic_figures(demo))
        notebook = config.project_root / "notebooks/detection_tracking/01_synthetic_demo.ipynb"
        export_synthetic_demo(demo, figures, output / "detection-report", notebook=notebook)
        cases = analyze_synthetic_cases(demo)
        case_figures = build_case_figures(cases)
        figures.update(case_figures)
        export_case_analysis(demo, cases, case_figures, output / "case-report", notebook=notebook)
        tracking_demo = load_tracking_demo(tracking["development"], tracking["evaluation"], input_pins=pins)
        tracking_figures = build_tracking_figures(tracking_demo)
        figures.update(tracking_figures)
        export_tracking_demo(tracking_demo, tracking_figures, output / "tracking-report")
        manifest.update(status="complete", source_manifest_sha256=pins, tracking_summary=tracking_demo["summary"],
                        freeze_manifest_sha256=_digest(freeze / "manifest.json"),
                        pair_reference_sha256=_digest(output / "pair-reference.json"), figures=len(figures))
    except BaseException as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__)
        raise
    finally:
        for figure in figures.values():
            plt.close(figure)
        manifest["wall_seconds"] = perf_counter() - started
        _save(path, manifest)
    return output
