class JPackError(Exception):
    """Base exception for all jtoken errors."""


class JPackEncodeError(JPackError):
    """Raised when encoding a dict fails."""


class JPackDecodeError(JPackError):
    """Raised when decoding a jtoken string fails."""


class NormalizationError(JPackError):
    """Raised when input normalization fails."""


class DenormalizationError(JPackError):
    """Raised when output denormalization fails."""
