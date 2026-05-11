from __future__ import annotations

import json
from typing import Any

from .exceptions import DenormalizationError
from .formats import OutputFormat
from .normalize import NormalizationContext


def denormalize(
    data: dict[str, Any],
    *,
    target: str = OutputFormat.PYTHON.value,
    context: NormalizationContext,
) -> Any:
    fmt = OutputFormat(target)
    if fmt not in (OutputFormat.PYTHON, OutputFormat.JSON) and not _has_restoration_context(
        context, fmt
    ):
        raise DenormalizationError(
            f"Output format {target!r} requires a normalization context sidecar"
        )

    restored = _rebuild_lists_at_paths(data, context, "")
    restored = _apply_typed_values(restored, context, fmt)
    if fmt == OutputFormat.ELASTIC_HIT:
        return _wrap_elastic_hit(restored, context)
    return restored


def render_output(value: Any, *, target: str = OutputFormat.PYTHON.value) -> str:
    fmt = OutputFormat(target)
    if fmt == OutputFormat.PYTHON:
        return repr(value)
    if fmt == OutputFormat.JSON:
        return json.dumps(value, indent=2, sort_keys=True) + "\n"
    if fmt == OutputFormat.MONGO_EXTENDED:
        return json.dumps(value, indent=2, sort_keys=True) + "\n"
    if fmt == OutputFormat.MONGO_SHELL:
        return _render_mongo_shell(value) + "\n"
    if fmt in (OutputFormat.ELASTIC_HIT, OutputFormat.ELASTIC_SOURCE):
        return json.dumps(value, indent=2, sort_keys=True) + "\n"
    raise DenormalizationError(f"Unsupported output format: {target!r}")


def decode_document(
    text: str,
    *,
    target: str = OutputFormat.PYTHON.value,
    context: NormalizationContext,
) -> Any:
    from ._codec import decode

    return denormalize(decode(text), target=target, context=context)


def _has_restoration_context(context: NormalizationContext, fmt: OutputFormat) -> bool:
    if fmt in (OutputFormat.MONGO_EXTENDED, OutputFormat.MONGO_SHELL):
        return bool(context.typed_values) or context.source_format in (
            "mongo_extended",
            "mongo_shell",
        )
    if fmt == OutputFormat.ELASTIC_HIT:
        return context.elastic is not None
    return True


def _rebuild_lists_at_paths(
    value: Any,
    context: NormalizationContext,
    path: str,
) -> Any:
    if isinstance(value, dict):
        rebuilt = {
            key: _rebuild_lists_at_paths(child, context, _join_path(path, key))
            for key, child in value.items()
        }
        if path in context.lists and _is_indexed_dict(rebuilt):
            return [
                rebuilt[str(index)]
                for index in _sorted_indices(rebuilt)
            ]
        return rebuilt
    return value


def _is_indexed_dict(value: dict[str, Any]) -> bool:
    if not value:
        return True
    return all(key.isdigit() for key in value)


def _sorted_indices(value: dict[str, Any]) -> list[int]:
    return sorted(int(key) for key in value)


def _apply_typed_values(value: Any, context: NormalizationContext, fmt: OutputFormat) -> Any:
    if fmt in (OutputFormat.PYTHON, OutputFormat.JSON, OutputFormat.ELASTIC_SOURCE):
        return value
    if fmt == OutputFormat.MONGO_EXTENDED:
        return _apply_mongo_extended(value, context, "")
    if fmt == OutputFormat.MONGO_SHELL:
        return _apply_mongo_shell(value, context, "")
    if fmt == OutputFormat.ELASTIC_HIT:
        return value
    return value


def _apply_mongo_extended(value: Any, context: NormalizationContext, path: str) -> Any:
    if isinstance(value, dict):
        if path in context.lists and _is_indexed_dict(value):
            return [
                _apply_mongo_extended(value[str(index)], context, _join_path(path, str(index)))
                for index in _sorted_indices(value)
            ]
        return {
            key: _apply_mongo_extended(child, context, _join_path(path, key))
            for key, child in value.items()
        }
    typed = context.typed_values.get(path)
    if typed == "object_id":
        return {"$oid": value}
    if typed == "datetime":
        return {"$date": value}
    if typed == "long" and isinstance(value, int):
        return {"$numberLong": str(value)}
    return value


def _apply_mongo_shell(value: Any, context: NormalizationContext, path: str) -> Any:
    if isinstance(value, dict):
        if path in context.lists and _is_indexed_dict(value):
            return [
                _apply_mongo_shell(value[str(index)], context, _join_path(path, str(index)))
                for index in _sorted_indices(value)
            ]
        return {
            key: _apply_mongo_shell(child, context, _join_path(path, key))
            for key, child in value.items()
        }
    typed = context.typed_values.get(path)
    if typed == "object_id":
        return f'ObjectId("{value}")'
    if typed == "datetime":
        return f'ISODate("{value}")'
    if typed == "long" and isinstance(value, int):
        return f"NumberLong({value})"
    return value


def _render_mongo_shell(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, list):
        if not value:
            return "[]"
        items = ",\n".join(f"{pad}    {_render_mongo_shell(item, indent + 4)}" for item in value)
        return f"[\n{items}\n{pad}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key, child in value.items():
            rendered = _render_mongo_shell(child, indent + 4)
            lines.append(f'{pad}    "{key}" : {rendered}')
        return "{\n" + ",\n".join(lines) + f"\n{pad}}}"
    if isinstance(value, str) and value.startswith(("ObjectId(", "ISODate(", "NumberLong(")):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return json.dumps(value)


def _wrap_elastic_hit(source: dict[str, Any], context: NormalizationContext) -> dict[str, Any]:
    elastic = context.elastic or {}
    envelope = dict(elastic.get("envelope", {}))
    hit = dict(envelope)
    hit["_source"] = source
    if elastic.get("had_fields"):
        hit["fields"] = _build_elastic_fields(source)
    return hit


def _build_elastic_fields(value: Any, prefix: str = "") -> dict[str, list[Any]]:
    fields: dict[str, list[Any]] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = _join_path(prefix, key)
            if isinstance(child, dict):
                fields.update(_build_elastic_fields(child, path))
            elif isinstance(child, list):
                fields[path] = child
            else:
                fields[path] = [child]
        return fields
    return fields


def _join_path(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key
