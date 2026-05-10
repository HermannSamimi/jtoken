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
    """Token comparison between jpack and JSON representations."""

    jpack_tokens: int
    json_tokens: int

    @property
    def saved(self) -> int:
        return self.json_tokens - self.jpack_tokens

    @property
    def percent(self) -> float:
        if self.json_tokens == 0:
            return 0.0
        return self.saved / self.json_tokens * 100

    def __str__(self) -> str:
        return (
            f"jpack: {self.jpack_tokens} tokens | "
            f"json: {self.json_tokens} tokens | "
            f"saved: {self.saved} ({self.percent:.1f}%)"
        )


def count_tokens(
    data: Union[dict[str, Any], str],
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
) -> int:
    """Count the LLM tokens in jpack-encoded data.

    Args:
        data:    A dict (auto-encoded to jpack) or an already-encoded jpack string.
        model:   tiktoken encoding or model name (default: cl100k_base, used by
                 GPT-4 and a close approximation for Claude).
                 Accepts encoding names ("cl100k_base", "o200k_base") or
                 OpenAI model names ("gpt-4", "gpt-4o").
        backend: "auto"     — tiktoken if installed, otherwise estimates.
                 "tiktoken" — tiktoken required; raises TokenCountError if absent.
                 "estimate" — always uses the ~4 chars/token heuristic.

    Returns:
        Integer token count for the jpack representation.
    """
    text = encode(data) if isinstance(data, dict) else data
    return _count(text, model=model, backend=backend)


def token_savings(
    data: Union[dict[str, Any], str],
    *,
    model: str = "cl100k_base",
    backend: str = "auto",
) -> TokenSavings:
    """Compare token usage between jpack and JSON for the same data.

    Args:
        data:    A dict or an already-encoded jpack string.
        model:   tiktoken encoding or model name (see count_tokens).
        backend: counting backend (see count_tokens).

    Returns:
        TokenSavings with jpack_tokens, json_tokens, saved, and percent.

    Example::

        stats = jpack.token_savings({"name": "Alice", "age": 30, "active": True})
        print(stats)
        # jpack: 8 tokens | json: 12 tokens | saved: 4 (33.3%)
    """
    if isinstance(data, str):
        source_dict = decode(data)
        jpack_text = data
    else:
        source_dict = data
        jpack_text = encode(data)

    json_text = json.dumps(source_dict)

    jpack_n = _count(jpack_text, model=model, backend=backend)
    json_n = _count(json_text, model=model, backend=backend)

    return TokenSavings(jpack_tokens=jpack_n, json_tokens=json_n)


def _count(text: str, *, model: str, backend: str) -> int:
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
                    raise TokenCountError(
                        f"Unknown tiktoken model/encoding: {model!r}"
                    ) from exc
                return _estimate(text)
        return len(enc.encode(text))

    return _estimate(text)


def _estimate(text: str) -> int:
    """~4 characters per token heuristic."""
    return max(1, (len(text) + 3) // 4) if text else 0
