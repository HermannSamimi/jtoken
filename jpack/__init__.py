"""jpack — Compress JSON for LLM prompts with ~30% fewer tokens."""

from ._codec import decode, encode
from .exceptions import JPackDecodeError, JPackEncodeError, JPackError
from .tokens import TokenCountError, TokenSavings, count_tokens, token_savings

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
    "token_savings",
    "TokenSavings",
    "JPackError",
    "JPackEncodeError",
    "JPackDecodeError",
    "TokenCountError",
    "__version__",
    "__author__",
]
