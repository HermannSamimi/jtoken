from __future__ import annotations

from typing import Any

from .exceptions import JPackDecodeError, JPackEncodeError

_SEP = ": "
_NULLS_KEY = "nulls"
_TRUES_KEY = "trues"
_FALSES_KEY = "falses"
_RESERVED = {_NULLS_KEY, _TRUES_KEY, _FALSES_KEY}


def encode(data: dict[str, Any]) -> str:
    """Compress a JSON-like dict into jpack format.

    Strips JSON syntax and collapses all null, true, and false fields each into
    a single summary line. Nested dicts are flattened with dot notation.
    The result is lossless: decode(encode(data)) == data.
    """
    if not isinstance(data, dict):
        raise JPackEncodeError(f"Expected dict, got {type(data).__name__}")

    flat = _flatten(data)

    null_keys: list[str] = []
    true_keys: list[str] = []
    false_keys: list[str] = []
    lines: list[str] = []

    for k, v in flat.items():
        if v is None:
            null_keys.append(k)
        elif v is True:
            true_keys.append(k)
        elif v is False:
            false_keys.append(k)
        elif isinstance(v, (int, float)):
            lines.append(f"{k}{_SEP}{v}")
        elif isinstance(v, str):
            val = f'"{v}"' if _is_ambiguous(v) else v
            lines.append(f"{k}{_SEP}{val}")
        else:
            raise JPackEncodeError(
                f"Unsupported value type for key {k!r}: {type(v).__name__}. "
                "Supported types: str, int, float, bool, None."
            )

    if true_keys:
        lines.append(f"{_TRUES_KEY}{_SEP}{','.join(true_keys)}")
    if false_keys:
        lines.append(f"{_FALSES_KEY}{_SEP}{','.join(false_keys)}")
    if null_keys:
        lines.append(f"{_NULLS_KEY}{_SEP}{','.join(null_keys)}")

    return "\n".join(lines)


def decode(text: str) -> dict[str, Any]:
    """Reconstruct a dict from a jpack-compressed string."""
    if not isinstance(text, str):
        raise JPackDecodeError(f"Expected str, got {type(text).__name__}")

    flat: dict[str, Any] = {}

    for lineno, line in enumerate(text.strip().splitlines(), 1):
        if not line.strip():
            continue
        if _SEP not in line:
            raise JPackDecodeError(
                f"Invalid format on line {lineno}: missing {_SEP!r} separator"
            )

        key, _, value = line.partition(_SEP)

        if key == _NULLS_KEY:
            for k in value.split(","):
                flat[k.strip()] = None
        elif key == _TRUES_KEY:
            for k in value.split(","):
                flat[k.strip()] = True
        elif key == _FALSES_KEY:
            for k in value.split(","):
                flat[k.strip()] = False
        elif _is_quoted(value):
            flat[key] = value[1:-1]
        elif value.lower() == "true":
            flat[key] = True   # backward-compat with inline key: true
        elif value.lower() == "false":
            flat[key] = False  # backward-compat with inline key: false
        else:
            try:
                flat[key] = int(value)
            except ValueError:
                try:
                    flat[key] = float(value)
                except ValueError:
                    flat[key] = value

    return _unflatten(flat)


# ── helpers ───────────────────────────────────────────────────────────────────

def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Recursively flatten a nested dict using dot-notation keys."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        k_str = str(k)
        if "." in k_str:
            raise JPackEncodeError(
                f"Key {k_str!r} contains '.' which is reserved for nested paths"
            )
        if _SEP in k_str:
            raise JPackEncodeError(f"Key cannot contain {_SEP!r}: {k_str!r}")
        if not prefix and k_str in _RESERVED:
            raise JPackEncodeError(f"Key '{k_str}' is reserved")
        key = f"{prefix}.{k_str}" if prefix else k_str
        if isinstance(v, dict):
            result.update(_flatten(v, key))
        else:
            result[key] = v
    return result


def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a nested dict from dot-notation keys."""
    result: dict[str, Any] = {}
    for dotted_key, value in flat.items():
        parts = dotted_key.split(".")
        d = result
        for part in parts[:-1]:
            if part not in d or not isinstance(d[part], dict):
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
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
