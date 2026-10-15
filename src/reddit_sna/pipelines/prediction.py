"""Trâm–Anh: synthetic community table → temporal split → baselines → metrics."""

from reddit_sna.config import RunConfig
from reddit_sna.pipelines import PipelineNotImplemented


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "prediction is scaffold-only: implement sample generation, temporal splits, "
        "baseline training and evaluation before running it"
    )
