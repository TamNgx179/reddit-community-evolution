"""Thin entry modules compose domain functions; pipelines never import each other."""


class PipelineNotImplemented(NotImplementedError):
    """The selected research pipeline has not been implemented yet."""
