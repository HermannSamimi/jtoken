# jpack

A lightweight, human-readable key-value serialization format for Python.

## What is jpack?

jpack encodes Python dictionaries into a plain-text, line-oriented format. Each key-value pair lives on its own line, making jpack data easy to read, write, and diff — with no brackets, quotes, or nesting overhead.

```
name: Alice
age: 30
active: true
score: 9.5
nulls: nickname,last_login
```

## Installation

```bash
# Core (no external dependencies)
pip install jpack

# With LLM token counting support
pip install jpack[tiktoken]
```

## Quick Start

```python
import jpack

data = {
    "name": "Alice",
    "age": 30,
    "active": True,
    "score": 9.5,
    "nickname": None,
}

text = jpack.encode(data)
print(text)
# name: Alice
# age: 30
# active: true
# score: 9.5
# nulls: nickname

result = jpack.decode(text)
# {"name": "Alice", "age": 30, "active": True, "score": 9.5, "nickname": None}

assert result == data  # round-trip safe
```

`dumps` and `loads` are available as `json`-style aliases:

```python
text = jpack.dumps(data)
data = jpack.loads(text)
```

## API

### `jpack.encode(data: dict) -> str`

Encodes a dictionary into a jpack-formatted string.

**Supported value types:** `str`, `int`, `float`, `bool`, `None`

Raises `JPackEncodeError` if:
- `data` is not a `dict`
- A key contains the reserved separator `": "`
- A key is named `"nulls"` (reserved by the format)
- A value's type is not supported (e.g. `list`, `dict`)

### `jpack.decode(text: str) -> dict`

Decodes a jpack-formatted string into a dictionary.

**Type inference on decode:**

| jpack value | Python type |
|---|---|
| `true` / `false` (case-insensitive) | `bool` |
| Integer literal, e.g. `42` | `int` |
| Float literal, e.g. `3.14` | `float` |
| Anything else | `str` |
| Key listed in `nulls:` line | `None` |

Raises `JPackDecodeError` if the input is not a valid jpack string.

### `jpack.count_tokens(data, *, model="cl100k_base", backend="auto") -> int`

Counts the LLM tokens in jpack-encoded data. Useful for budgeting context when using jpack-serialized data in prompts.

```python
import jpack

data = {"name": "Alice", "age": 30, "active": True}

# Auto: uses tiktoken if installed, otherwise estimates (~4 chars/token)
n = jpack.count_tokens(data)

# Force tiktoken with a specific model or encoding name
n = jpack.count_tokens(data, model="gpt-4")           # by model name
n = jpack.count_tokens(data, model="cl100k_base")     # by encoding name
n = jpack.count_tokens(data, model="o200k_base")      # GPT-4o encoding

# Force the estimator (no tiktoken required)
n = jpack.count_tokens(data, backend="estimate")

# Also accepts an already-encoded string
text = jpack.encode(data)
n = jpack.count_tokens(text)
```

| `backend` | Behaviour |
|---|---|
| `"auto"` (default) | tiktoken if installed, otherwise estimates |
| `"tiktoken"` | tiktoken required; raises `TokenCountError` if not installed |
| `"estimate"` | always uses the ~4 chars/token heuristic, no extra dependency |

Raises `TokenCountError` (a subclass of `JPackError`) if `backend="tiktoken"` and tiktoken is not installed, or if the model name is unrecognised.

## Format Specification

- Each key-value pair occupies exactly one line: `key: value`
- The separator is `": "` (colon + space)
- `None` values are omitted inline; their keys are collected at the end in a single `nulls: key1,key2,...` line
- Booleans are written as lowercase `true` or `false`
- Keys must not contain `": "` and must not be `"nulls"`
- Multi-line string values are not supported

## Exceptions

```
JPackError
├── JPackEncodeError
├── JPackDecodeError
└── TokenCountError
```

```python
from jpack import JPackEncodeError, JPackDecodeError

try:
    jpack.decode("malformed")
except JPackDecodeError as e:
    print(e)
```

## Development

```bash
git clone https://github.com/hermannsamimi/jpack
cd jpack
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage report
pytest --cov=jpack --cov-report=term-missing
```

## License

MIT — © 2026 Hermann Samimi
