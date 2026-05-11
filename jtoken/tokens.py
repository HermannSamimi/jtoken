from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Union

from ._codec import decode, encode
from .exceptions import JPackError

try:
    import tiktoken as _tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


class TokenCountError(JPackError):
    """Raised when token counting cannot be completed."""


@dataclass
class TokenSavings:
    """Token comparison between jtoken and JSON representations."""

    jtoken_tokens: int
    json_tokens: int

    @property
    def saved(self) -> int:
        return self.json_tokens - self.jtoken_tokens

    @property
    def percent(self) -> float:
        if self.json_tokens == 0:
            return 0.0
        return self.saved / self.json_tokens * 100

    def __str__(self) -> str:
        return (
            f"jtoken: {self.jtoken_tokens} tokens | "
            f"json: {self.json_tokens} tokens | "
            f"saved: {self.saved} ({self.percent:.1f}%)"
        )


def count_tokens(
    data: Union[dict[str, Any], str],
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
) -> int:
    """Count the LLM tokens in jtoken-encoded data.

    Args:
        data:    A dict (auto-encoded to jtoken) or an already-encoded jtoken string.
        model:   tiktoken encoding or model name (default: cl100k_base, used by
                 GPT-4 and a close approximation for Claude).
                 Accepts encoding names ("cl100k_base", "o200k_base") or
                 OpenAI model names ("gpt-4", "gpt-4o").
        backend: "auto"     — tiktoken if installed, otherwise estimates.
                 "tiktoken" — tiktoken required; raises TokenCountError if absent.
                 "estimate" — always uses the ~4 chars/token heuristic.

    Returns:
        Integer token count for the jtoken representation.
    """
    text = encode(data) if isinstance(data, dict) else data
    return _count(text, model=model, backend=backend)


def count_text_tokens(
    text: str,
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
) -> int:
    """Count LLM tokens in a raw text string."""
    return _count(text, model=model, backend=backend)


def token_savings(
    data: Union[dict[str, Any], str],
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
    json_indent: int | None = 2,
) -> TokenSavings:
    """Compare token usage between jtoken and JSON for the same data.

    Args:
        data:    A dict or an already-encoded jtoken string.
        model:   tiktoken encoding or model name (see count_tokens).
        backend: counting backend (see count_tokens).
        json_indent: indentation for the JSON baseline. Use ``2`` for
            prompt-style pretty JSON, or ``None`` for compact JSON.

    Returns:
        TokenSavings with jtoken_tokens, json_tokens, saved, and percent.

    Example::

        stats = jtoken.token_savings({"name": "Alice", "age": 30, "active": True})
        print(stats)
        # jtoken: 8 tokens | json: 12 tokens | saved: 4 (33.3%)
    """
    if isinstance(data, str):
        source_dict = decode(data)
        jtoken_text = data
    else:
        source_dict = data
        jtoken_text = encode(data)

    if json_indent is None:
        json_text = json.dumps(source_dict, ensure_ascii=False, separators=(",", ":"))
    else:
        json_text = json.dumps(source_dict, ensure_ascii=False, indent=json_indent)

    jtoken_n = _count(jtoken_text, model=model, backend=backend)
    json_n = _count(json_text, model=model, backend=backend)

    return TokenSavings(jtoken_tokens=jtoken_n, json_tokens=json_n)


def _count(text: str, *, model: str, backend: str) -> int:
    if backend == "estimate":
        return _estimate(text)

    if backend == "tiktoken" and not _TIKTOKEN_AVAILABLE:
        raise TokenCountError(
            "tiktoken is not installed. Run: pip install jtoken[tiktoken]"
        )

    if _TIKTOKEN_AVAILABLE and backend in ("auto", "tiktoken"):
        try:
            enc = _tiktoken.encoding_for_model(model)
        except KeyError:
            try:
                enc = _tiktoken.get_encoding(model)
            except Exception as exc:
                if backend == "tiktoken":
                    raise TokenCountError(
                        f"Unknown tiktoken model/encoding: {model!r}"
                    ) from exc
                return _estimate(text)
        return len(enc.encode(text))

    return _estimate(text)


def _estimate(text: str) -> int:
    """~4 characters per token heuristic."""
    return max(1, (len(text) + 3) // 4) if text else 0
