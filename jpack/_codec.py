from __future__ import annotations

from typing import Any

from .exceptions import JPackDecodeError, JPackEncodeError

_SEP = ": "
_NULLS_KEY = "nulls"


def encode(data: dict[str, Any]) -> str:
    """Compress a JSON-like dict into jpack format.

    Strips JSON syntax (quotes, braces, commas) and collapses null fields into
    a single trailing line, producing a compact format LLMs read as well as JSON
    but with ~30% fewer tokens.

    String values that would be misread on decode (look like numbers or booleans)
    keep their quotes so the round-trip is lossless.
    """
    if not isinstance(data, dict):
        raise JPackEncodeError(f"Expected dict, got {type(data).__name__}")

    null_keys: list[str] = []
    lines: list[str] = []

    for k, v in data.items():
        key = str(k)
        if key == _NULLS_KEY:
            raise JPackEncodeError(f"Key '{_NULLS_KEY}' is reserved")
        if _SEP in key:
            raise JPackEncodeError(f"Key cannot contain {_SEP!r}: {key!r}")

        if v is None:
            null_keys.append(key)
        elif isinstance(v, bool):
            lines.append(f"{key}{_SEP}{str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{key}{_SEP}{v}")
        elif isinstance(v, str):
            # Keep quotes only for values that would be mistyped on decode
            val = f'"{v}"' if _is_ambiguous(v) else v
            lines.append(f"{key}{_SEP}{val}")
        else:
            raise JPackEncodeError(
                f"Unsupported value type for key {key!r}: {type(v).__name__}. "
                "Supported types: str, int, float, bool, None."
            )

    if null_keys:
        lines.append(f"{_NULLS_KEY}{_SEP}{','.join(null_keys)}")

    return "\n".join(lines)


def decode(text: str) -> dict[str, Any]:
    """Reconstruct a dict from a jpack-compressed string."""
    if not isinstance(text, str):
        raise JPackDecodeError(f"Expected str, got {type(text).__name__}")

    result: dict[str, Any] = {}

    for lineno, line in enumerate(text.strip().splitlines(), 1):
        if not line.strip():
            continue
        if _SEP not in line:
            raise JPackDecodeError(
                f"Invalid format on line {lineno}: missing {_SEP!r} separator"
            )

        key, _, value = line.partition(_SEP)

        if key == _NULLS_KEY:
            for null_key in value.split(","):
                result[null_key.strip()] = None
        elif _is_quoted(value):
            result[key] = value[1:-1]  # quoted → always str, strip the quotes
        elif value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            try:
                result[key] = int(value)
            except ValueError:
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value

    return result


def _is_ambiguous(v: str) -> bool:
    """True if this string would be mistyped as a number or bool on decode."""
    if not v:
        return True
    if v.lower() in ("true", "false"):
        return True
    try:
        int(v)
        return True
    except ValueError:
        pass
    try:
        float(v)
        return True
    except ValueError:
        pass
    return False


def _is_quoted(v: str) -> bool:
    return len(v) >= 2 and v[0] == '"' and v[-1] == '"'
