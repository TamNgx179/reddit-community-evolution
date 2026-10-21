"""Run the synthetic notebook in a fresh kernel using this Python interpreter.

Replay saved detection and tracking outputs. Install the project [notebook] extra
first; the T02 bundle and fixed tracking pair runs are required. Preserve old evidence.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new replay directory inside project artifacts")
    parser.add_argument("--report", type=Path, required=True, help="new execution-evidence directory inside project artifacts")
    parser.add_argument("--cwd", type=Path, help="kernel cwd; default is the notebook directory")
    parser.add_argument("--tracking-development", type=Path)
    parser.add_argument("--tracking-evaluation", type=Path)
    parser.add_argument("--reference", type=Path, help="Explicit trusted current-run or legacy delivery reference JSON")
    args = parser.parse_args()
    root, bundle, output, report = (p.resolve() for p in (args.project, args.bundle, args.output, args.report))
    source = root / "notebooks/detection_tracking/01_synthetic_demo.ipynb"
    case_output = output.with_name(output.name + "-cases")
    tracking_output = output.with_name(output.name + "-tracking")
    pair = root / "artifacts/detection-tracking/phuc-dang-final-20261020-001"
    tracking_inputs = ((args.tracking_development or pair / "development").resolve(),
                       (args.tracking_evaluation or pair / "evaluation").resolve())
    cwd = args.cwd.resolve() if args.cwd else source.parent
    artifacts = root / "artifacts"
    if not source.is_file() or not (bundle / "delivery-manifest.json").is_file() or not cwd.is_dir():
        parser.error("project notebook, extracted T02 bundle and existing kernel cwd are required")
    if any(not (p / "manifest.json").is_file() for p in tracking_inputs):
        parser.error("run scripts/run_tracking_handoff.py first, or pass both tracking split directories")
    destinations = (output, case_output, tracking_output, report)
    for target in destinations:
        if target.exists() or not target.is_relative_to(artifacts) or target.is_relative_to(bundle) or bundle.is_relative_to(target):
            parser.error("output, sibling -cases and report must be new, inside artifacts and separate from inputs")
        if any(target.is_relative_to(p) or p.is_relative_to(target) for p in tracking_inputs):
            parser.error("outputs must not overlap tracking inputs")
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(destinations) for b in destinations[i+1:]):
        parser.error("output, sibling -cases and report must not overlap each other")

    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    nb = nbformat.read(source, 4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == "code"]
    if not code or any(c.outputs or c.execution_count is not None for c in code):
        parser.error("source notebook must have code cells without cached execution/output")
    digest = lambda p: sha256(p.read_bytes()).hexdigest()
    source_hash = digest(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True)
    reference = (args.reference or root / "configs/legacy-handoff-reference.json").resolve()
    if not reference.is_file():
        parser.error("delivery reference is required; use the new run's pair-reference.json or the legacy reference")
    env = {"REDDIT_SNA_PROJECT": str(root), "REDDIT_SYNTHETIC_BUNDLE": str(bundle),
           "REDDIT_SYNTHETIC_REFERENCE": str(reference),
           "REDDIT_SYNTHETIC_DEMO_OUTPUT": str(output), "REDDIT_SYNTHETIC_DEMO_DATASET": "dev-grow-easy-g11",
           "REDDIT_TRACKING_DEVELOPMENT": str(tracking_inputs[0]), "REDDIT_TRACKING_EVALUATION": str(tracking_inputs[1])}
    previous = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    km = KernelManager(kernel_name="python3")
    km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    km.kernel_spec.env = dict(km.kernel_spec.env, PYTHONHASHSEED="0")
    client = NotebookClient(nb, km=km, timeout=240, allow_errors=False, record_timing=True,
                            resources={"metadata": {"path": str(cwd)}})
    started, status = perf_counter(), "failed"
    try:
        client.execute(cleanup_kc=True)
        assert [c.execution_count for c in code] == list(range(1, len(code) + 1))
        assert digest(source) == source_hash, "source notebook changed during execution"
        for directory, figures in ((output, 4), (case_output, 2), (tracking_output, 2)):
            metadata = json.loads((directory / "metadata.json").read_bytes())
            assert metadata["status"] == "complete" and metadata["figure_count"] == figures
            assert not (directory / "failure.json").exists()
            for name, info in metadata["files"].items():
                assert digest(directory / name) == info["sha256"] and (directory / name).stat().st_size == info["bytes"]
            assert sum(p.is_file() for p in directory.rglob("*")) == len(metadata["files"]) + 1
        status = "complete"
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        nbformat.write(nb, report / "01_synthetic_demo.executed.ipynb")
        records = [{"cell": i, "execution_count": c.execution_count,
                    "errors": [dict(o) for o in c.get("outputs", []) if o.output_type == "error"]}
                   for i, c in enumerate(nb.cells) if c.cell_type == "code"]
        result = {"status": status, "finished_at": datetime.now(timezone.utc).isoformat(),
                  "seconds": perf_counter() - started, "source_sha256": source_hash,
                  "python": sys.executable, "kernel_cwd": str(cwd), "environment": env,
                  "cells": records, "png_outputs": sum("image/png" in o.get("data", {}) for c in nb.cells for o in c.get("outputs", [])),
                  "scope": "saved synthetic detection and fixed PR12 tracking replay; no detector rerun or partner acceptance"}
        (report / "notebook-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "seconds", "png_outputs", "python")}))


if __name__ == "__main__":
    main()
