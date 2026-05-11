# jtoken

Compress JSON for LLM prompts — same data, fewer tokens.

## What it does

jtoken strips the syntactic noise from JSON (`"`, `{}`, `,`) and collapses all
`null`, `true`, and `false` fields each into a single summary line. Nested dicts
are flattened with dot notation so the same collapse applies at every level.
The result is a compact format an LLM reads just as well as JSON.

**JSON (30 tokens):**
```json
{"name": "Alice", "age": 30, "active": true, "verified": false, "ref": null}
```

**jtoken (21 tokens):**
```
name: Alice
age: 30
trues: active
falses: verified
nulls: ref
```

The round-trip is lossless: `decode(encode(data)) == data` for all supported types.

## Installation

```bash
# Core — no external dependencies
pip install jtoken

# With accurate LLM token counting
pip install jtoken[tiktoken]
```

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
# user: alice
# age: 30
# score: 9.5
# trues: premium,verified
# falses: is_remote,trial
# nulls: referral,last_login

original = jtoken.decode(text)
assert original == data
```

`dumps` / `loads` are available as `json`-style aliases.

## Normalization and denormalization

Foreign document shapes such as Elasticsearch hits, MongoDB Extended JSON, and
Mongo shell literals can be normalized into the scalar dict model before encoding.
Use a sidecar normalization context file to restore the original dialect after
decode.

```python
import jtoken

raw_hit = {...}  # Elasticsearch hit with _source and fields
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

Supported input dialects: `auto`, `json`, `python`, `mongo_extended`,
`mongo_shell`, `elastic_hit`, and `elastic_source`.

Supported output dialects: `python`, `json`, `mongo_extended`, `mongo_shell`,
`elastic_hit`, and `elastic_source`.

## CLI

```bash
echo '{"name": "Alice", "active": true}' | jtoken encode
echo 'name: Alice\ntrues: active' | jtoken decode
echo '{"name": "Alice", "active": true}' | jtoken stats
echo '{"name": "Alice", "active": true}' | jtoken count
```

Use `-f/--file` to read from a file instead of stdin. `stats` and `count` accept
`--model` and `--backend` (`auto`, `tiktoken`, `estimate`).

## Nested documents

Nested dicts are flattened with dot notation. Booleans and nulls at any depth
are collapsed into the same summary lines.

```python
data = {
    "title": "Engineer",
    "metadata": {
        "verified": True,
        "sponsored": False,
        "score": None,
        "source": {
            "crawled": True,
            "enriched": None,
        },
    },
}

print(jtoken.encode(data))
# title: Engineer
# trues: metadata.verified,metadata.source.crawled
# falses: metadata.sponsored
# nulls: metadata.score,metadata.source.enriched
```

Decode reconstructs the full nested structure:

```python
assert jtoken.decode(jtoken.encode(data)) == data  # ✓
```

**Limitation:** keys cannot contain `.` (reserved for nesting) or `": "`.
Arrays are not supported.

## Token savings

```python
import jtoken

stats = jtoken.token_savings(data)
print(stats)
# jtoken: 22 tokens | json: 36 tokens | saved: 14 (38.9%)

n = jtoken.count_tokens(data)  # count jtoken tokens only
```

Savings are compared against `json.dumps(data)` — the standard representation
you'd paste into a prompt. Savings are highest when a document has many `null`
or boolean fields.

```python
# Specify model or encoding
stats = jtoken.token_savings(data, model="gpt-4o")
stats = jtoken.token_savings(data, model="o200k_base")

# No tiktoken dependency
stats = jtoken.token_savings(data, backend="estimate")
```

## API

### `encode(data: dict) -> str`

Compresses a dict into jtoken. Supported value types: `str`, `int`, `float`,
`bool`, `None`, nested `dict`.

**Summary lines (always at the end):**

| line | contains |
|---|---|
| `trues: k1,k2,...` | all keys whose value is `True` |
| `falses: k1,k2,...` | all keys whose value is `False` |
| `nulls: k1,k2,...` | all keys whose value is `None` |

String values that would decode ambiguously (look like a number or boolean)
keep their quotes:

```python
jtoken.encode({"zip": "90210"})  # → 'zip: "90210"'   (string, quotes kept)
jtoken.encode({"zip":  90210})   # → 'zip: 90210'      (int, no quotes)
jtoken.encode({"ok": "true"})    # → 'ok: "true"'      (string, quotes kept)
jtoken.encode({"ok": True})      # → 'trues: ok'       (bool, collapsed)
```

Raises `JPackEncodeError` for unsupported types, dots or `": "` in keys, or
reserved key names (`nulls`, `trues`, `falses`).

### `decode(text: str) -> dict`

Reconstructs the original dict, including nested structure from dot-notation
keys. Type inference for scalar values:

| value | decoded as |
|---|---|
| `"quoted"` | `str` (always) |
| key in `trues:` line | `True` |
| key in `falses:` line | `False` |
| key in `nulls:` line | `None` |
| integer literal, e.g. `42` | `int` |
| float literal, e.g. `3.14` | `float` |
| anything else | `str` |

Raises `JPackDecodeError` for invalid input.

### `token_savings(data, *, model, backend) -> TokenSavings`

Compares jtoken vs `json.dumps` token usage.

```python
stats.jtoken_tokens   # int
stats.json_tokens    # int
stats.saved          # int
stats.percent        # float
str(stats)           # "jtoken: 22 tokens | json: 36 tokens | saved: 14 (38.9%)"
```

### `count_tokens(data, *, model, backend) -> int`

Counts LLM tokens in the jtoken representation. Accepts a dict or an
already-encoded jtoken string.

**`backend` options:**

| value | behaviour |
|---|---|
| `"auto"` (default) | tiktoken if installed, otherwise estimates |
| `"tiktoken"` | requires tiktoken; raises `TokenCountError` if absent |
| `"estimate"` | ~4 chars/token heuristic, no extra dependency |

## Exceptions

```
JPackError
├── JPackEncodeError
├── JPackDecodeError
└── TokenCountError
```

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
