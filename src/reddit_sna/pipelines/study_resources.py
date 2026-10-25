"""Monitor a study worker's process tree and preserve truthful stop evidence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import time


def json_write(path, value):
    """Atomically replace a caller-owned journal, never an input artifact."""
    path = Path(path)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pending.replace(path)


def disk_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())


def monitored(command, root, stage, protocol):
    """Run one worker, stop its tree on resource excess and retain its exit code.

    RSS is sampled at one-second intervals and summed over the monitor and
    worker descendants. Brief allocation peaks can escape sampling; report this
    limitation. This is an observed-resource stop, not an OS memory reservation.
    """
    import psutil
    root = Path(root)
    journal = root / "resources" / f"{stage}.json"
    journal.parent.mkdir(parents=True, exist_ok=True)
    if journal.exists():
        raise FileExistsError("Resource journal exists; do not overwrite a previous stage attempt")
    if shutil.disk_usage(root).free < protocol["minimum_free_gib"] * 2**30:
        raise ValueError("Insufficient free disk before study phase")
    report = dict(stage=stage, status="started", command=command,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  peak_process_tree_rss_bytes=0, measurement="one-second sampled RSS; subsecond peaks may be missed")
    json_write(journal, report)
    started = time.perf_counter()
    process = None
    try:
        with (journal.with_suffix(".log")).open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            worker = psutil.Process(process.pid)
            tick = 0
            while process.poll() is None:
                rss = psutil.Process().memory_info().rss
                try:
                    for child in [worker] + worker.children(recursive=True):
                        try:
                            rss += child.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
                report["peak_process_tree_rss_bytes"] = max(report["peak_process_tree_rss_bytes"], rss)
                exceeded = rss > protocol["memory_budget_gib"] * 2**30
                if tick % 10 == 0:
                    used = disk_bytes(root)
                    report["working_bytes"] = used
                    exceeded |= used > protocol["working_budget_gib"] * 2**30
                    exceeded |= shutil.disk_usage(root).free < protocol["minimum_free_gib"] * 2**30
                    json_write(journal, report)
                if exceeded:
                    report["status"] = "resource_exceeded"
                    raise RuntimeError("Study resource limit exceeded")
                tick += 1
                time.sleep(1)
            report["exit_code"] = process.returncode
            report["status"] = "complete" if process.returncode == 0 else "failed"
            if process.returncode:
                raise RuntimeError(f"Study worker failed; inspect {journal.with_suffix('.log').name}")
    except BaseException:
        if process is not None and process.poll() is None:
            try:
                descendants = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                descendants = []
            for child in reversed(descendants):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            process.kill()
            process.wait()
        if report["status"] == "started":
            report["status"] = "failed_or_interrupted"
        raise
    finally:
        report["wall_seconds"] = time.perf_counter() - started
        json_write(journal, report)
    return report
