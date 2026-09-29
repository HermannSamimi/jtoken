"""Tests for JSONTokenDocumentTransformer (langchain-core is required)."""

import pytest

langchain_core = pytest.importorskip("langchain_core")
from langchain_core.documents import Document  # noqa: E402

from langchain_jtoken import JSONTokenDocumentTransformer  # noqa: E402

JSON_DOC = Document(page_content='{"user": "alice", "premium": true, "verified": true, "ref": null}')
PROSE_DOC = Document(page_content="Just some plain prose, not JSON at all.")


def test_transforms_json_document():
    out = JSONTokenDocumentTransformer().transform_documents([JSON_DOC])
    assert out[0].page_content == "user: alice\ntrues: premium,verified\nnulls: ref"


def test_metadata_preserved_and_original_untouched():
    doc = Document(page_content='{"a": 1}', metadata={"id": 7})
    out = JSONTokenDocumentTransformer().transform_documents([doc])
    assert out[0].metadata == {"id": 7}
    assert doc.page_content == '{"a": 1}'


def test_non_json_passthrough_and_strict():
    out = JSONTokenDocumentTransformer().transform_documents([PROSE_DOC])
    assert out[0] is PROSE_DOC
    with pytest.raises(Exception):
        JSONTokenDocumentTransformer(strict=True).transform_documents([PROSE_DOC])