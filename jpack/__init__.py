"""jpack — A lightweight, human-readable key-value serialization format."""

from ._codec import decode, encode
from .exceptions import JPackDecodeError, JPackEncodeError, JPackError

__version__ = "0.1.0"
__author__ = "Hermann Samimi"

# json-style aliases
dumps = encode
loads = decode

__all__ = [
    "encode",
    "decode",
    "dumps",
    "loads",
    "JPackError",
    "JPackEncodeError",
    "JPackDecodeError",
    "__version__",
    "__author__",
]
