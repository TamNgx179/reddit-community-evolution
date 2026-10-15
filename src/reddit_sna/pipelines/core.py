"""Tâm–Thanh: Reddit → snapshots → communities → labels/features → model → metrics."""

from reddit_sna.config import RunConfig
from reddit_sna.pipelines import PipelineNotImplemented


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "core is scaffold-only: implement Reddit preparation, detection, tracking, "
        "features, forecasting and evaluation before running it"
    )
