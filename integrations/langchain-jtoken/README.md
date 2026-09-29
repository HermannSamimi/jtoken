# langchain-jtoken

A [LangChain](https://python.langchain.com) document transformer that compresses
JSON-shaped `Document.page_content` with [jtoken](https://github.com/HermannSamimi/jtoken)
so retrieved documents (Elasticsearch hits, MongoDB JSON, API responses) occupy
fewer tokens in the LLM context window — **losslessly**, so any agent can decode
them back with `jtoken.decode_document` when needed.

Measurable wins (tiktoken, cl100k_base): **−11%** Elasticsearch hits, **−19%**
MongoDB extended JSON, **−13%** nested API events on the
[reproducible benchmark](../../benchmarks/benchmark.py).

## Install

```bash
pip install langchain-jtoken
```

## Usage

```python
from langchain_jtoken import JSONTokenDocumentTransformer

transformer = JSONTokenDocumentTransformer()
compressed_docs = transformer.transform_documents(docs)
```

Non-JSON content passes through unchanged (`strict=True` raises instead).

## Test

```bash
pytest
```

MIT — © Hermann Samimi