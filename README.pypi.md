# jtoken

**Author:** Hermann Samimi

**jtoken** compresses JSON-shaped documents for LLM prompts: fewer tokens, readable line-oriented output, and lossless round-trip for supported scalar nested dicts. It includes normalization for Elasticsearch hits and MongoDB JSON, a CLI, and token measurement helpers.

Python 3.8+.

## Installation

### Core (no extra runtime dependencies)

```bash
pip install jtoken
```

### With accurate OpenAI-style token counting

```bash
pip install "jtoken[tiktoken]"
```

The core package uses only the Python standard library. Install the `tiktoken` extra when you want tokenizer-accurate counts for OpenAI-compatible models.

## Quick start

```python
import jtoken

data = {
    "user": "alice",
    "age": 30,
    "premium": True,
    "verified": True,
    "is_remote": False,
    "trial": False,
    "score": 9.5,
    "referral": None,
    "last_login": None,
}

text = jtoken.encode(data)
restored = jtoken.decode(text)
assert restored == data
```

Aliases: `jtoken.dumps` = `encode`, `jtoken.loads` = `decode`.

## End-to-end document workflow

```python
import jtoken

raw = open("hit.json", encoding="utf-8").read()
text, context = jtoken.encode_document(raw, source="elastic_hit")
restored = jtoken.decode_document(text, target="elastic_hit", context=context)
```

Keep the normalization context sidecar when you need a lossless decode back into Mongo shell, Extended JSON, or an Elasticsearch hit envelope.

## Format overview

**JSON**

```json
{"name": "Alice", "age": 30, "active": true, "verified": false, "ref": null}
```

**jtoken**

```text
name: Alice
age: 30
trues: active
falses: verified
nulls: ref
```

### Encoding rules

- Nested dicts flatten with dot notation.
- `True`, `False`, and `None` collapse into `trues:`, `falses:`, and `nulls:` summary lines.
- Ambiguous strings keep quotes on encode.
- Multiline strings are JSON-quoted on one line.
- Keys containing `.` are escaped during normalization and restored from context.

### Supported scalar types

`str`, `int`, `float`, `bool`, `None`, and nested `dict`.

### Limitations

- Keys cannot contain `": "` in the core codec.
- Reserved top-level keys: `nulls`, `trues`, `falses`.
- Lists are normalized into nested dicts with numeric keys before encoding.

## Public API reference

### Package metadata

| name | type | description |
|---|---|---|
| `jtoken.__version__` | `str` | package version |
| `jtoken.__author__` | `str` | author name (`Hermann Samimi`) |

### Core codec

| function | signature | description |
|---|---|---|
| `encode` | `encode(data: dict) -> str` | compress a nested scalar dict into jtoken text |
| `decode` | `decode(text: str) -> dict` | reconstruct the nested dict |
| `dumps` | alias of `encode` | json-style alias |
| `loads` | alias of `decode` | json-style alias |

### Normalization and denormalization

| function | signature | description |
|---|---|---|
| `parse_input` | `parse_input(text, *, source="auto")` | parse foreign text into Python data |
| `normalize` | `normalize(data, *, source="auto", context=None)` | return `(normalized_dict, NormalizationContext)` |
| `denormalize` | `denormalize(data, *, target="python", context)` | restore lists, typed values, and dialect shape |
| `render_output` | `render_output(value, *, target="python") -> str` | render denormalized data as text |
| `encode_document` | `encode_document(raw, *, source="auto", context=None)` | return `(jtoken_text, NormalizationContext)` |
| `decode_document` | `decode_document(text, *, target="python", context)` | decode jtoken text and denormalize |

### Token measurement

| function | signature | description |
|---|---|---|
| `count_tokens` | `count_tokens(data, *, model="cl100k_base", backend="auto") -> int` | count tokens for a dict or encoded jtoken string |
| `count_text_tokens` | `count_text_tokens(text, *, model="cl100k_base", backend="auto") -> int` | count tokens for raw text |
| `token_savings` | `token_savings(data, *, model="cl100k_base", backend="auto", json_indent=2)` | compare jtoken vs pretty JSON token usage |

### `TokenSavings` properties

| property | type | description |
|---|---|---|
| `jtoken_tokens` | `int` | token count for the jtoken representation |
| `json_tokens` | `int` | token count for the JSON baseline |
| `saved` | `int` | `json_tokens - jtoken_tokens` |
| `percent` | `float` | percent saved relative to JSON |

`str(stats)` prints a one-line summary.

### `NormalizationContext` fields

| field | type | description |
|---|---|---|
| `source_format` | `str` | input dialect used during normalization |
| `target_format` | `str \| None` | optional output hint |
| `typed_values` | `dict[str, str]` | dotted paths with BSON-like type markers |
| `lists` | `set[str]` | dotted paths that were lists before flattening |
| `dotted_keys` | `dict[str, str]` | escaped keys that originally contained `.` |
| `elastic` | `dict \| None` | Elasticsearch envelope metadata |

Methods: `to_dict()`, `from_dict(data)`.

### Format enums

`InputFormat`: `auto`, `json`, `python`, `mongo_extended`, `mongo_shell`, `elastic_hit`, `elastic_source`

`OutputFormat`: `python`, `json`, `mongo_extended`, `mongo_shell`, `elastic_hit`, `elastic_source`

### Exceptions

| exception | base | when raised |
|---|---|---|
| `JPackError` | `Exception` | base library error |
| `JPackEncodeError` | `JPackError` | encoding fails |
| `JPackDecodeError` | `JPackError` | decoding fails |
| `NormalizationError` | `JPackError` | normalization fails |
| `DenormalizationError` | `JPackError` | denormalization fails |
| `TokenCountError` | `JPackError` | token counting fails |

## Token counting

```python
stats = jtoken.token_savings(data, model="gpt-4o", backend="tiktoken", json_indent=2)
print(stats.jtoken_tokens, stats.json_tokens, stats.saved, stats.percent)
```

| `backend` | behavior |
|---|---|
| `auto` | use `tiktoken` when installed, otherwise estimate |
| `tiktoken` | require `tiktoken` |
| `estimate` | simple character heuristic |

`json_indent=2` compares against prompt-style pretty JSON. Use `json_indent=None` for compact JSON.

## CLI

```bash
jtoken encode --input-format mongo_shell -f doc.json --context-out doc.ctx.json
jtoken decode --output-format mongo_shell -f doc.jtoken --context-in doc.ctx.json
jtoken stats --input-format json -f doc.json --model gpt-4o --backend tiktoken
jtoken count --input-format json -f doc.json --backend estimate
python -m jtoken encode
```

Common flags:

- `-f/--file`
- `--input-format`
- `--output-format`
- `--context-out`
- `--context-in`
- `--model`
- `--backend`

## Links

- Homepage: https://github.com/hermannsamimi/jtoken
- Repository: https://github.com/hermannsamimi/jtoken
- Issues: https://github.com/hermannsamimi/jtoken/issues

## License

MIT — Copyright (c) 2026 Hermann Samimi
