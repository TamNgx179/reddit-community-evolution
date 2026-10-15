"""Detection/tracking pipeline: synthetic dynamic graph → detection/tracking → benchmark metrics."""

from reddit_sna.config import RunConfig
from reddit_sna.pipelines import PipelineNotImplemented


def run(config: RunConfig) -> None:
    raise PipelineNotImplemented(
        "detection-tracking is scaffold-only: implement graph benchmark generation, "
        "detection, tracking and evaluation before running it"
    )
