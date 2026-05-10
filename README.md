# jpack

Compress JSON for LLM prompts — same data, fewer tokens.

## What it does

jpack strips the syntactic noise from JSON (`"`, `{}`, `,`) and collapses all
`null`, `true`, and `false` fields each into a single summary line. Nested dicts
are flattened with dot notation so the same collapse applies at every level.
The result is a compact format an LLM reads just as well as JSON.

**JSON (30 tokens):**
```json
{"name": "Alice", "age": 30, "active": true, "verified": false, "ref": null}
```

**jpack (21 tokens):**
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
pip install jpack

# With accurate LLM token counting
pip install jpack[tiktoken]
```

## Quick start

```python
import jpack

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

text = jpack.encode(data)
# user: alice
# age: 30
# score: 9.5
# trues: premium,verified
# falses: is_remote,trial
# nulls: referral,last_login

original = jpack.decode(text)
assert original == data
```

`dumps` / `loads` are available as `json`-style aliases.

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

print(jpack.encode(data))
# title: Engineer
# trues: metadata.verified,metadata.source.crawled
# falses: metadata.sponsored
# nulls: metadata.score,metadata.source.enriched
```

Decode reconstructs the full nested structure:

```python
assert jpack.decode(jpack.encode(data)) == data  # ✓
```

**Limitation:** keys cannot contain `.` (reserved for nesting) or `": "`.
Arrays are not supported.

## Token savings

```python
import jpack

stats = jpack.token_savings(data)
print(stats)
# jpack: 22 tokens | json: 36 tokens | saved: 14 (38.9%)

n = jpack.count_tokens(data)  # count jpack tokens only
```

Savings are compared against `json.dumps(data)` — the standard representation
you'd paste into a prompt. Savings are highest when a document has many `null`
or boolean fields.

```python
# Specify model or encoding
stats = jpack.token_savings(data, model="gpt-4o")
stats = jpack.token_savings(data, model="o200k_base")

# No tiktoken dependency
stats = jpack.token_savings(data, backend="estimate")
```

## API

### `encode(data: dict) -> str`

Compresses a dict into jpack. Supported value types: `str`, `int`, `float`,
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
jpack.encode({"zip": "90210"})  # → 'zip: "90210"'   (string, quotes kept)
jpack.encode({"zip":  90210})   # → 'zip: 90210'      (int, no quotes)
jpack.encode({"ok": "true"})    # → 'ok: "true"'      (string, quotes kept)
jpack.encode({"ok": True})      # → 'trues: ok'       (bool, collapsed)
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

Compares jpack vs `json.dumps` token usage.

```python
stats.jpack_tokens   # int
stats.json_tokens    # int
stats.saved          # int
stats.percent        # float
str(stats)           # "jpack: 22 tokens | json: 36 tokens | saved: 14 (38.9%)"
```

### `count_tokens(data, *, model, backend) -> int`

Counts LLM tokens in the jpack representation. Accepts a dict or an
already-encoded jpack string.

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
git clone https://github.com/hermannsamimi/jpack
cd jpack
pip install -e ".[dev]"
pytest
pytest --cov=jpack --cov-report=term-missing
```

## License

MIT — © 2026 Hermann Samimi
