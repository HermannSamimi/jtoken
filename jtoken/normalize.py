from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .exceptions import NormalizationError
from .formats import InputFormat

_ELASTIC_ENVELOPE_KEYS = ("_index", "_id", "_version", "_score", "_type", "_routing")
_MONGO_SHELL_OBJECT_ID = re.compile(r'ObjectId\(\s*"([0-9a-fA-F]{24})"\s*\)')
_MONGO_SHELL_ISO_DATE = re.compile(r'ISODate\(\s*"([^"]+)"\s*\)')
_MONGO_SHELL_NUMBER_INT = re.compile(r"NumberInt\(\s*(-?\d+)\s*\)")
_MONGO_SHELL_NUMBER_LONG = re.compile(r"NumberLong\(\s*(-?\d+)\s*\)")
_DOTTED_KEY_MARKER = "__DOT__"
_MONGO_EXTENDED_KEYS = {
    "$oid",
    "$date",
    "$numberInt",
    "$numberLong",
    "$numberDouble",
    "$numberDecimal",
}


@dataclass
class NormalizationContext:
    source_format: str = InputFormat.JSON.value
    target_format: str | None = None
    typed_values: dict[str, str] = field(default_factory=dict)
    lists: set[str] = field(default_factory=set)
    dotted_keys: dict[str, str] = field(default_factory=dict)
    elastic: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_format": self.source_format,
            "target_format": self.target_format,
            "typed_values": dict(self.typed_values),
            "lists": sorted(self.lists),
            "dotted_keys": dict(self.dotted_keys),
            "elastic": self.elastic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizationContext:
        return cls(
            source_format=data.get("source_format", InputFormat.JSON.value),
            target_format=data.get("target_format"),
            typed_values=dict(data.get("typed_values", {})),
            lists=set(data.get("lists", [])),
            dotted_keys=dict(data.get("dotted_keys", {})),
            elastic=data.get("elastic"),
        )


def parse_input(text: str, *, source: str = InputFormat.AUTO.value) -> Any:
    fmt = _resolve_input_format(text, source)
    if fmt in (InputFormat.JSON, InputFormat.PYTHON):
        return _parse_json(text)
    if fmt == InputFormat.MONGO_SHELL:
        return _parse_json(_preprocess_mongo_shell(text))
    if fmt == InputFormat.MONGO_EXTENDED:
        return _parse_json(text)
    if fmt in (InputFormat.ELASTIC_HIT, InputFormat.ELASTIC_SOURCE):
        data = _parse_json(text)
        if not isinstance(data, dict):
            raise NormalizationError("Expected a JSON object")
        return data
    raise NormalizationError(f"Unsupported input format: {source!r}")


def normalize(
    data: Any,
    *,
    source: str = InputFormat.AUTO.value,
    context: NormalizationContext | None = None,
) -> tuple[dict[str, Any], NormalizationContext]:
    ctx = context or NormalizationContext()
    if isinstance(data, str):
        data = parse_input(data, source=source)
    data = _coerce_root_document(data, ctx)

    if source != InputFormat.AUTO.value:
        fmt = InputFormat(source)
    else:
        fmt = _detect_dict_format(data)

    ctx.source_format = fmt.value
    working = _prepare_working_document(data, fmt, ctx)
    if fmt in (InputFormat.MONGO_EXTENDED, InputFormat.MONGO_SHELL):
        working = _convert_mongo_extended(working, ctx, "")
    working = _sanitize_dotted_keys(working, ctx, "")
    normalized = _flatten_lists(working, ctx, "")
    normalized = _coerce_scalars(normalized, ctx, "")
    return normalized, ctx


def encode_document(
    raw: Any,
    *,
    source: str = InputFormat.AUTO.value,
    context: NormalizationContext | None = None,
) -> tuple[str, NormalizationContext]:
    from ._codec import encode

    normalized, ctx = normalize(raw, source=source, context=context)
    return encode(normalized), ctx


def _resolve_input_format(text: str, source: str) -> InputFormat:
    if source != InputFormat.AUTO.value:
        return InputFormat(source)
    stripped = text.lstrip()
    if _MONGO_SHELL_OBJECT_ID.search(text) or _MONGO_SHELL_ISO_DATE.search(text):
        return InputFormat.MONGO_SHELL
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise NormalizationError(f"Invalid JSON input: {exc}") from exc
        return _detect_parsed_format(data)
    raise NormalizationError("Could not detect input format")


def _coerce_root_document(
    data: Any,
    ctx: NormalizationContext,
) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        ctx.lists.add("")
        if not data:
            return {}
        return {str(index): item for index, item in enumerate(data)}
    raise NormalizationError(f"Expected dict or list, got {type(data).__name__}")


def _detect_parsed_format(data: Any) -> InputFormat:
    if isinstance(data, dict):
        return _detect_dict_format(data)
    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return _detect_dict_format(data[0])
        return InputFormat.JSON
    raise NormalizationError("Expected a JSON object or array")


def _detect_dict_format(data: dict[str, Any]) -> InputFormat:
    if "_source" in data and isinstance(data.get("_source"), dict):
        return InputFormat.ELASTIC_HIT
    if _contains_mongo_extended(data):
        return InputFormat.MONGO_EXTENDED
    return InputFormat.JSON


def _contains_mongo_extended(value: Any) -> bool:
    if isinstance(value, dict):
        if set(value.keys()) & _MONGO_EXTENDED_KEYS:
            return True
        return any(_contains_mongo_extended(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_mongo_extended(item) for item in value)
    return False


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"Invalid JSON input: {exc}") from exc


def _preprocess_mongo_shell(text: str) -> str:
    text = _MONGO_SHELL_OBJECT_ID.sub(r'{"$oid": "\1"}', text)
    text = _MONGO_SHELL_ISO_DATE.sub(r'{"$date": "\1"}', text)
    text = _MONGO_SHELL_NUMBER_INT.sub(r"\1", text)
    text = _MONGO_SHELL_NUMBER_LONG.sub(r'{"$numberLong": "\1"}', text)
    return text


def _prepare_working_document(
    data: dict[str, Any],
    fmt: InputFormat,
    ctx: NormalizationContext,
) -> dict[str, Any]:
    if fmt == InputFormat.ELASTIC_HIT:
        return _prepare_elastic_hit(data, ctx)
    if fmt == InputFormat.ELASTIC_SOURCE:
        source = data.get("_source", data)
        if not isinstance(source, dict):
            raise NormalizationError("elastic_source input must be an object")
        return dict(source)
    return dict(data)


def _prepare_elastic_hit(data: dict[str, Any], ctx: NormalizationContext) -> dict[str, Any]:
    source = data.get("_source")
    if not isinstance(source, dict):
        raise NormalizationError("elastic_hit input requires an object _source")

    envelope = {key: data[key] for key in _ELASTIC_ENVELOPE_KEYS if key in data}
    fields = data.get("fields")
    skipped_fields: list[str] = []
    merged = dict(source)

    if isinstance(fields, dict):
        for dotted_key, raw_value in fields.items():
            value = _unwrap_elastic_field_value(raw_value)
            if _path_exists(merged, dotted_key):
                skipped_fields.append(dotted_key)
                continue
            _set_dotted_path(merged, dotted_key, value)

    ctx.elastic = {
        "envelope": envelope,
        "had_fields": isinstance(fields, dict),
        "skipped_fields": skipped_fields,
    }
    return merged


def _unwrap_elastic_field_value(value: Any) -> Any:
    if isinstance(value, list):
        if len(value) == 1:
            return value[0]
        return value
    return value


def _path_exists(data: dict[str, Any], dotted_key: str) -> bool:
    parts = dotted_key.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _set_dotted_path(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current = data
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def _convert_mongo_extended(
    value: Any,
    ctx: NormalizationContext,
    path: str,
) -> Any:
    if isinstance(value, list):
        return [_convert_mongo_extended(item, ctx, path) for item in value]
    if not isinstance(value, dict):
        return value

    keys = set(value.keys())
    if keys == {"$oid"}:
        oid = str(value["$oid"]).lower()
        if path:
            ctx.typed_values[path] = "object_id"
        return oid
    if keys == {"$date"}:
        date_value = value["$date"]
        if isinstance(date_value, dict) and "$numberLong" in date_value:
            date_value = date_value["$numberLong"]
        iso = str(date_value)
        if path:
            ctx.typed_values[path] = "datetime"
        return iso
    if keys == {"$numberInt"}:
        return int(value["$numberInt"])
    if keys == {"$numberLong"}:
        number = int(value["$numberLong"])
        if path:
            ctx.typed_values[path] = "long"
        return number
    if keys == {"$numberDouble"}:
        return float(value["$numberDouble"])
    if keys == {"$numberDecimal"}:
        return str(value["$numberDecimal"])

    return {
        key: _convert_mongo_extended(child, ctx, _join_path(path, key))
        for key, child in value.items()
    }


def _sanitize_dotted_keys(
    value: Any,
    ctx: NormalizationContext,
    path: str,
) -> Any:
    if isinstance(value, list):
        return [
            _sanitize_dotted_keys(item, ctx, _join_path(path, str(index)))
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            safe_key = key.replace(".", _DOTTED_KEY_MARKER) if "." in key else key
            child_path = _join_path(path, safe_key)
            if safe_key != key:
                ctx.dotted_keys[child_path] = key
            sanitized[safe_key] = _sanitize_dotted_keys(child, ctx, child_path)
        return sanitized
    return value


def _flatten_lists(
    value: Any,
    ctx: NormalizationContext,
    path: str,
) -> Any:
    if isinstance(value, list):
        if path:
            ctx.lists.add(path)
        if not value:
            return {}
        return {
            str(index): _flatten_lists(item, ctx, _join_path(path, str(index)))
            for index, item in enumerate(value)
        }
    if isinstance(value, dict):
        return {
            key: _flatten_lists(child, ctx, _join_path(path, key))
            for key, child in value.items()
        }
    return value


def _coerce_scalars(
    value: Any,
    ctx: NormalizationContext,
    path: str,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _coerce_scalars(child, ctx, _join_path(path, key))
            for key, child in value.items()
        }
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    raise NormalizationError(
        f"Unsupported value type at {path or '<root>'}: {type(value).__name__}"
    )


def _join_path(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key
