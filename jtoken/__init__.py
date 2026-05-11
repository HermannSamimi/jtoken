"""jtoken — Compress JSON for LLM prompts with ~30% fewer tokens."""

from ._codec import decode, encode
from .denormalize import decode_document, denormalize, render_output
from .exceptions import (
    DenormalizationError,
    JPackDecodeError,
    JPackEncodeError,
    JPackError,
    NormalizationError,
)
from .formats import InputFormat, OutputFormat
from .normalize import NormalizationContext, encode_document, normalize, parse_input
from .tokens import (
    TokenCountError,
    TokenSavings,
    count_text_tokens,
    count_tokens,
    token_savings,
)

__version__ = "0.3.0"
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
    "count_text_tokens",
    "token_savings",
    "TokenSavings",
    "JPackError",
    "JPackEncodeError",
    "JPackDecodeError",
    "NormalizationError",
    "DenormalizationError",
    "InputFormat",
    "OutputFormat",
    "NormalizationContext",
    "parse_input",
    "normalize",
    "denormalize",
    "render_output",
    "encode_document",
    "decode_document",
    "TokenCountError",
    "__version__",
    "__author__",
]
