# jpack

Compress JSON for LLM prompts — same data, ~30% fewer tokens.

## What it does

jpack strips the syntactic noise from JSON (`"`, `{}`, `,`) and collapses all `null` fields into a single line. The result is a compact key-value format that an LLM reads just as well as JSON, but costs significantly fewer tokens.

**JSON (30 tokens):**
```json
{"name": "Alice", "age": 30, "active": true, "score": 9.5, "ref": null}
```

**jpack (24 tokens):**
```
name: Alice
age: 30
active: true
score: 9.5
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
    "score": 9.5,
    "referral": None,
    "last_login": None,
}

# Compress for an LLM prompt
text = jpack.encode(data)
# user: alice
# age: 30
# premium: true
# score: 9.5
# nulls: referral,last_login

# Reconstruct the original dict
original = jpack.decode(text)
assert original == data
```

`dumps` / `loads` are available as `json`-style aliases.

## Token savings

```python
import jpack

data = {"name": "Alice", "role": "admin", "active": True, "score": 9.5,
        "bio": None, "last_login": None, "referral": None}

stats = jpack.token_savings(data)
print(stats)
# jpack: 22 tokens | json: 36 tokens | saved: 14 (38.9%)

# Count jpack tokens only
n = jpack.count_tokens(data)
```

`token_savings` and `count_tokens` compare against standard `json.dumps` output (the default you'd paste into a prompt). They use **tiktoken** when installed and fall back to a ~4 chars/token estimate otherwise.

```python
# Force a specific model or encoding
stats = jpack.token_savings(data, model="gpt-4o")
stats = jpack.token_savings(data, model="o200k_base")

# No tiktoken needed
stats = jpack.token_savings(data, backend="estimate")
```

## API

### `encode(data: dict) -> str`

Strips JSON syntax and returns a compact jpack string. Supported value types: `str`, `int`, `float`, `bool`, `None`.

String values that would decode ambiguously (look like a number or boolean) keep their quotes so the round-trip is lossless:

```python
jpack.encode({"zip": "90210"})   # → 'zip: "90210"'  (quotes kept)
jpack.encode({"zip":  90210})    # → 'zip: 90210'    (no quotes — it's an int)
```

Raises `JPackEncodeError` for unsupported types or reserved keys.

### `decode(text: str) -> dict`

Reconstructs the original dict from a jpack string. Type inference:

| value | decoded as |
|---|---|
| `"quoted"` | `str` (always) |
| `true` / `false` (any case) | `bool` |
| integer literal, e.g. `42` | `int` |
| float literal, e.g. `3.14` | `float` |
| anything else | `str` |
| key in `nulls:` line | `None` |

Raises `JPackDecodeError` for invalid input.

### `token_savings(data, *, model, backend) -> TokenSavings`

Returns a `TokenSavings` object comparing jpack vs `json.dumps` token usage.

```python
stats.jpack_tokens   # int
stats.json_tokens    # int
stats.saved          # int  (json_tokens - jpack_tokens)
stats.percent        # float
str(stats)           # "jpack: 22 tokens | json: 36 tokens | saved: 14 (38.9%)"
```

### `count_tokens(data, *, model, backend) -> int`

Counts LLM tokens in the jpack representation of `data`. Accepts a dict or an already-encoded jpack string.

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

## Limitations

- Flat dicts only — nested objects and arrays are not supported.
- String values that contain a literal newline cannot be encoded.

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
