from __future__ import annotations

from typing import Any, Union

from ._codec import encode
from .exceptions import JPackError

try:
    import tiktoken as _tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


class TokenCountError(JPackError):
    """Raised when token counting cannot be completed."""


def count_tokens(
    data: Union[dict[str, Any], str],
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
) -> int:
    """Count the LLM tokens in jpack-encoded data.

    Args:
        data:    A dict (auto-encoded) or an already-encoded jpack string.
        model:   tiktoken encoding or model name (default: cl100k_base).
                 Accepts encoding names ("cl100k_base", "o200k_base") or
                 OpenAI model names ("gpt-4", "gpt-4o").
        backend: "auto"     — tiktoken if installed, otherwise estimates.
                 "tiktoken" — tiktoken required; raises if not installed.
                 "estimate" — always uses the ~4 chars/token heuristic.

    Returns:
        Integer token count.

    Raises:
        TokenCountError: if backend="tiktoken" and tiktoken is not installed,
                         or if the model name is unrecognised by tiktoken.
    """
    text = encode(data) if isinstance(data, dict) else data

    if backend == "estimate":
        return _estimate(text)

    if backend == "tiktoken" and not _TIKTOKEN_AVAILABLE:
        raise TokenCountError(
            "tiktoken is not installed. Run: pip install jpack[tiktoken]"
        )

    if _TIKTOKEN_AVAILABLE and backend in ("auto", "tiktoken"):
        try:
            enc = _tiktoken.encoding_for_model(model)
        except KeyError:
            try:
                enc = _tiktoken.get_encoding(model)
            except Exception as exc:
                if backend == "tiktoken":
                    raise TokenCountError(f"Unknown tiktoken model/encoding: {model!r}") from exc
                return _estimate(text)
        return len(enc.encode(text))

    return _estimate(text)


def _estimate(text: str) -> int:
    """~4 characters per token heuristic (reasonable for English prose)."""
    return max(1, (len(text) + 3) // 4) if text else 0
