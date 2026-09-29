"""A LangChain DocumentTransformer that compresses JSON page_content with jtoken.

Uses the lossless, line-oriented ``jtoken`` encoding so that Retrieved
documents (JSON blobs from Elasticsearch, MongoDB, or plain APIs) take
fewer tokens in the LLM context window while remaining readable.
"""

from __future__ import annotations

from typing import Sequence, cast

from langchain_core.documents import BaseDocumentTransformer, Document

import jtoken


class JSONTokenDocumentTransformer(BaseDocumentTransformer):
    """Compress JSON-shaped ``Document.page_content`` using jtoken.

    Documents whose content is not valid JSON-shaped text are passed
    through unchanged when ``strict=False`` (default); in ``strict=True``
    mode they raise ``JPackEncodeError``.

    Example:
        .. code-block:: python

            from langchain_jtoken import JSONTokenDocumentTransformer

            transformer = JSONTokenDocumentTransformer()
            compressed = transformer.transform_documents(docs)
    """

    def __init__(self, *, strict: bool = False) -> None:
        """Args:
        strict: Raise on documents whose content cannot be encoded;
                otherwise leave them untouched.
        """
        self.strict = strict

    def transform_documents(
        self, documents: Sequence[Document], **kwargs: object
    ) -> Sequence[Document]:
        transformed: list[Document] = []
        for doc in documents:
            try:
                text = jtoken.encode_document(doc.page_content)[0]
            except jtoken.JPackError:
                if self.strict:
                    raise
                transformed.append(doc)
                continue
            transformed.append(
                _copy_with_content(doc, text)
            )
        return transformed

    async def atransform_documents(
        self, documents: Sequence[Document], **kwargs: object
    ) -> Sequence[Document]:
        return self.transform_documents(documents, **kwargs)


def _copy_with_content(doc: Document, new_content: str) -> Document:
    """Return a copy of ``doc`` with replaced page_content (metadata intact)."""
    clone = cast(Document, doc.model_copy(deep=True))
    clone.page_content = new_content
    return clone