class JPackError(Exception):
    """Base exception for all jpack errors."""


class JPackEncodeError(JPackError):
    """Raised when encoding a dict fails."""


class JPackDecodeError(JPackError):
    """Raised when decoding a jpack string fails."""
