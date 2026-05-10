from __future__ import annotations

from typing import Any

from .exceptions import JPackDecodeError, JPackEncodeError

_SEP = ": "
_NULLS_KEY = "nulls"


def encode(data: dict[str, Any]) -> str:
    """Encode a dictionary into a jpack-formatted string.

    Supported value types: str, int, float, bool, None.
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
            lines.append(f"{key}{_SEP}{v}")
        else:
            raise JPackEncodeError(
                f"Unsupported value type for key {key!r}: {type(v).__name__}. "
                "Supported types: str, int, float, bool, None."
            )

    if null_keys:
        lines.append(f"{_NULLS_KEY}{_SEP}{','.join(null_keys)}")

    return "\n".join(lines)


def decode(text: str) -> dict[str, Any]:
    """Decode a jpack-formatted string into a dictionary.

    Type inference: bool → int → float → str. None values come from the nulls line.
    """
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
