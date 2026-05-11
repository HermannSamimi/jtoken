# jtoken

Compress JSON for LLM prompts — same data, fewer tokens.

**Author:** Hermann Samimi

jtoken strips JSON syntactic noise, collapses repeated booleans and nulls into summary lines, flattens nested dicts with dot notation, and supports normalization for Elasticsearch hits and MongoDB JSON. The package ships as a stdlib-first library with an optional `tiktoken` extra and a `jtoken` CLI.

## Installation

### Core

```bash
pip install jtoken
```

No extra runtime dependencies.

### With tokenizer-accurate counting

```bash
pip install "jtoken[tiktoken]"
```

Use the `tiktoken` extra when you want OpenAI-compatible token counts instead of the built-in estimate backend.

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
original = jtoken.decode(text)
assert original == data
```

`dumps` / `loads` are json-style aliases for `encode` / `decode`.

## What the format looks like

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

Nested dicts flatten with dot notation. Booleans and nulls at any depth collapse into the same summary lines. Decode reconstructs the original nested structure.

## Normalization and denormalization

Foreign document shapes can be normalized before encoding and restored after decode with a sidecar context.

```python
import jtoken

raw_hit = {...}
normalized, context = jtoken.normalize(raw_hit, source="elastic_hit")
text = jtoken.encode(normalized)
restored = jtoken.denormalize(
    jtoken.decode(text),
    target="elastic_hit",
    context=context,
)
```

```bash
jtoken encode --input-format elastic_hit -f hit.json --context-out hit.ctx.json
jtoken decode --output-format mongo_shell -f hit.jtoken --context-in hit.ctx.json
```

### Input and output formats

Use `source=` / `target=` in Python or `--input-format` / `--output-format` on the CLI. `encode`, `stats`, and `count` accept `--input-format` (default `auto`). `decode` accepts `--output-format` (default `json`).

| Input (`source` / `--input-format`) | Use when |
|---|---|
| `auto` | Let jtoken detect the dialect from the text or object shape |
| `json` | Standard JSON object |
| `python` | Same JSON parser as `json` |
| `mongo_extended` | MongoDB Extended JSON with `$oid`, `$date`, `$numberInt`, `$numberLong`, `$numberDouble`, `$numberDecimal` |
| `mongo_shell` | MongoDB shell document with `ObjectId()`, `ISODate()`, `NumberInt()`, `NumberLong()` |
| `elastic_hit` | Elasticsearch search hit with `_source` (and optional `fields`) |
| `elastic_source` | `_source` payload only, or a document wrapped as `{"_source": {...}}` |

| Output (`target` / `--output-format`) | Use when |
|---|---|
| `python` | Python `repr` (Python API default) |
| `json` | Pretty-printed JSON (CLI `decode` default) |
| `mongo_extended` | Extended JSON; requires a context sidecar for BSON-like types |
| `mongo_shell` | Mongo shell document; requires a context sidecar for BSON-like types |
| `elastic_hit` | Full Elasticsearch hit envelope; requires a context sidecar |
| `elastic_source` | JSON shaped like an Elasticsearch `_source` wrapper |

With `auto`, jtoken picks `mongo_shell` when it sees `ObjectId(...)` or `ISODate(...)`, `elastic_hit` when the object has a dict `_source`, `mongo_extended` when Extended JSON markers such as `$oid` or `$date` appear, and otherwise `json`.

Write the normalization context to a sidecar on encode (`--context-out` / `NormalizationContext.to_dict()`) and pass it back on decode when the output dialect is not plain JSON or Python. The sidecar records list paths, dotted keys, Elasticsearch envelope metadata, and MongoDB type markers in `typed_values` (`object_id`, `datetime`, `long`).

### MongoDB shell and Extended JSON

Mongo shell input is parsed as JSON after rewriting shell literals: `ObjectId("...")` and `ISODate("...")` become Extended JSON, `NumberInt(n)` becomes a plain integer, and `NumberLong(n)` becomes `{"$numberLong": "n"}`. On normalize, `object_id`, `datetime`, and `long` values are stored in the context so `mongo_extended` and `mongo_shell` output can restore `{"$oid": ...}` / `ObjectId(...)`, `{"$date": ...}` / `ISODate(...)`, and `{"$numberLong": ...}` / `NumberLong(...)`. `$numberInt`, `$numberDouble`, and `$numberDecimal` are coerced to Python scalars and are not tracked in `typed_values`.

### Elasticsearch hits

`elastic_hit` encodes the merged `_source` document (plus any `fields` values that are not already present in `_source`) and stores `_index`, `_id`, `_version`, `_score`, `_type`, and `_routing` in the context for lossless `elastic_hit` output.

## CLI

```bash
echo '{"name": "Alice", "active": true}' | jtoken encode
echo 'name: Alice\ntrues: active' | jtoken decode
echo '{"name": "Alice", "active": true}' | jtoken stats
echo '{"name": "Alice", "active": true}' | jtoken count
```

Use `-f/--file` for file input. `encode`, `stats`, and `count` accept `--input-format`. `decode` accepts `--output-format` and `--context-in` when restoring non-JSON dialects. `stats` and `count` accept `--model` and `--backend`.

## Token savings

```python
import jtoken

stats = jtoken.token_savings(data, model="gpt-4o", backend="tiktoken", json_indent=2)
print(stats)
# jtoken: 22 tokens | json: 36 tokens | saved: 14 (38.9%)

print(stats.jtoken_tokens, stats.json_tokens, stats.saved, stats.percent)
```

`count_tokens` and `count_text_tokens` are also available. Savings compare the jtoken representation against pretty JSON by default (`json_indent=2`).

## API reference

### Package metadata

- `jtoken.__version__`
- `jtoken.__author__`

### Core codec

- `encode(data: dict) -> str`
- `decode(text: str) -> dict`
- `dumps` / `loads`

### Normalization

- `parse_input(text, *, source="auto")`
- `normalize(data, *, source="auto", context=None) -> tuple[dict, NormalizationContext]`
- `denormalize(data, *, target="python", context)`
- `render_output(value, *, target="python") -> str`
- `encode_document(raw, *, source="auto", context=None) -> tuple[str, NormalizationContext]`
- `decode_document(text, *, target="python", context)`

### Token helpers

- `count_tokens(data, *, model="cl100k_base", backend="auto") -> int`
- `count_text_tokens(text, *, model="cl100k_base", backend="auto") -> int`
- `token_savings(data, *, model="cl100k_base", backend="auto", json_indent=2) -> TokenSavings`

### `TokenSavings`

- `jtoken_tokens`
- `json_tokens`
- `saved`
- `percent`

### `NormalizationContext`

- `source_format`
- `target_format`
- `typed_values`
- `lists`
- `dotted_keys`
- `elastic`
- `to_dict()` / `from_dict()`

### Format enums

- `InputFormat`
- `OutputFormat`

### Exceptions

- `JPackError`
- `JPackEncodeError`
- `JPackDecodeError`
- `NormalizationError`
- `DenormalizationError`
- `TokenCountError`

## Development

```bash
git clone https://github.com/hermannsamimi/jtoken
cd jtoken
pip install -e ".[dev]"
pytest
pytest --cov=jtoken --cov-report=term-missing
```

## License

MIT — © 2026 Hermann Samimi
