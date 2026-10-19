"""Core pipeline: Reddit → snapshots → communities → labels/features → model → metrics."""

from reddit_sna.config import RunConfig
from reddit_sna.pipelines import PipelineNotImplemented


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "the generic core run entrypoint is scaffold-only; use week1 for the "
        "implemented baseline demo, or explicit prepare and forecast stages. "
        "HeTCo and the full proposed research pipeline remain planned"
    )
