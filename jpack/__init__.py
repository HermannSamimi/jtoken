"""jpack — A lightweight, human-readable key-value serialization format."""

from ._codec import decode, encode
from .exceptions import JPackDecodeError, JPackEncodeError, JPackError
from .tokens import TokenCountError, count_tokens

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
    "count_tokens",
    "JPackError",
    "JPackEncodeError",
    "JPackDecodeError",
    "TokenCountError",
    "__version__",
    "__author__",
]
