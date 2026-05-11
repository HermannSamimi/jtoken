from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import count_tokens, token_savings
from .denormalize import decode_document, render_output
from .exceptions import (
    DenormalizationError,
    JPackError,
    NormalizationError,
)
from .formats import INPUT_FORMAT_VALUES, OUTPUT_FORMAT_VALUES
from .normalize import NormalizationContext, encode_document, normalize
from .tokens import TokenCountError


def _read_input(path: str | None) -> str:
    if path:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    return sys.stdin.read()


def _load_json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("JSON input must be an object")
    return data


def _load_context(path: str | None) -> NormalizationContext:
    if not path:
        raise SystemExit("This output format requires --context-in")
    return NormalizationContext.from_dict(_load_json_object(_read_input(path)))


def _write_context(path: str, context: NormalizationContext) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(context.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _load_json_or_jtoken(text: str, input_format: str) -> dict[str, Any] | str:
    stripped = text.strip()
    if not stripped:
        raise SystemExit("Input is empty")
    if stripped[0] in "{[":
        normalized, _ = normalize(text, source=input_format)
        return normalized
    return stripped


def _handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (JPackError, TokenCountError, NormalizationError, DenormalizationError) as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(1) from exc

    return wrapper


@_handle_errors
def _cmd_encode(args: argparse.Namespace) -> None:
    raw = _read_input(args.file)
    text, context = encode_document(raw, source=args.input_format)
    sys.stdout.write(text)
    if args.context_out:
        _write_context(args.context_out, context)


@_handle_errors
def _cmd_decode(args: argparse.Namespace) -> None:
    text = _read_input(args.file)
    context = None
    if args.context_in:
        context = _load_context(args.context_in)
    data = decode_document(text, target=args.output_format, context=context)
    sys.stdout.write(render_output(data, target=args.output_format))


@_handle_errors
def _cmd_stats(args: argparse.Namespace) -> None:
    payload = _load_json_or_jtoken(_read_input(args.file), args.input_format)
    stats = token_savings(payload, model=args.model, backend=args.backend)
    print(stats)


@_handle_errors
def _cmd_count(args: argparse.Namespace) -> None:
    payload = _load_json_or_jtoken(_read_input(args.file), args.input_format)
    print(count_tokens(payload, model=args.model, backend=args.backend))


def _add_token_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        default="cl100k_base",
        help="tiktoken model or encoding name (default: cl100k_base)",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "tiktoken", "estimate"),
        default="auto",
        help="token counting backend (default: auto)",
    )


def _add_input_file(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--file",
        help="read input from a file instead of stdin",
    )


def _add_input_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input-format",
        choices=INPUT_FORMAT_VALUES,
        default="auto",
        help="input document dialect (default: auto)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jtoken", description="jtoken CLI")
    input_parent = argparse.ArgumentParser(add_help=False)
    _add_input_file(input_parent)
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_parser = subparsers.add_parser(
        "encode",
        parents=[input_parent],
        help="encode JSON to jtoken",
    )
    _add_input_format(encode_parser)
    encode_parser.add_argument(
        "--context-out",
        help="write normalization context sidecar to this path",
    )
    encode_parser.set_defaults(func=_cmd_encode)

    decode_parser = subparsers.add_parser(
        "decode",
        parents=[input_parent],
        help="decode jtoken to JSON",
    )
    decode_parser.add_argument(
        "--output-format",
        choices=OUTPUT_FORMAT_VALUES,
        default="json",
        help="output document dialect (default: json)",
    )
    decode_parser.add_argument(
        "--context-in",
        help="read normalization context sidecar from this path",
    )
    decode_parser.set_defaults(func=_cmd_decode)

    stats_parser = subparsers.add_parser(
        "stats",
        parents=[input_parent],
        help="compare jtoken vs JSON token usage",
    )
    _add_input_format(stats_parser)
    _add_token_flags(stats_parser)
    stats_parser.set_defaults(func=_cmd_stats)

    count_parser = subparsers.add_parser(
        "count",
        parents=[input_parent],
        help="count jtoken tokens",
    )
    _add_input_format(count_parser)
    _add_token_flags(count_parser)
    count_parser.set_defaults(func=_cmd_count)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
