"""Typed failures at the offline physical-model boundary."""


class DecoderViewError(ValueError):
    """Invalid metadata, selection, or sample shape."""


class SourceMismatchError(DecoderViewError):
    """A model or record map belongs to a different physical artifact."""


class UndefinedObservableError(DecoderViewError):
    """The requested outcome is not a reliable global logical observable."""


class DEMConstructionError(DecoderViewError):
    """Stim cannot represent the selected physical model under exact options."""


class UnsupportedProjectionError(DecoderViewError):
    """The requested projection/approximation mode is not implemented."""
