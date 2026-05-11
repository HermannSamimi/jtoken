import json

from jtoken import decode, denormalize, encode, encode_document, normalize
from jtoken.denormalize import decode_document
from jtoken.normalize import _CTX_LINE_PREFIX


MONGO_SHELL_DOC = """
{
    "_id" : ObjectId("69ca983fbf8c8953c43c2407"),
    "influencer" : "alice@example.com",
    "day" : ISODate("2026-02-12T00:00:00.000+0000"),
    "threshold" : 1.45,
    "tags" : [
        "forwarded",
        "drive"
    ],
    "real_time" : true
}
"""


def test_roundtrip_normalized_scalar_document():
    data = {"name": "Alice", "active": True, "ref": None}
    normalized, context = normalize(data, source="json")
    restored = denormalize(decode(encode(normalized)), target="json", context=context)
    assert restored == data


def test_roundtrip_mongo_shell_with_context():
    normalized, context = normalize(MONGO_SHELL_DOC, source="mongo_shell")
    text = encode(normalized)
    restored = denormalize(decode(text), target="mongo_extended", context=context)
    assert restored["_id"] == {"$oid": "69ca983fbf8c8953c43c2407"}
    assert restored["tags"] == ["forwarded", "drive"]
    assert restored["real_time"] is True


def test_encode_document_returns_text_and_context(tmp_path):
    text, context = encode_document(MONGO_SHELL_DOC, source="mongo_shell")
    assert "trues:" in text or "influencer:" in text
    assert context.typed_values["_id"] == "object_id"
    context_path = tmp_path / "ctx.json"
    context_path.write_text(json.dumps(context.to_dict()), encoding="utf-8")
    assert context_path.exists()


def test_encode_document_embeds_context_header():
    text, ctx = encode_document(MONGO_SHELL_DOC, source="mongo_shell")
    first_line = text.splitlines()[0]
    assert first_line.startswith(_CTX_LINE_PREFIX)
    embedded = json.loads(first_line[len(_CTX_LINE_PREFIX):])
    assert embedded["typed_values"]["_id"] == "object_id"
    assert "tags" in embedded["lists"]


def test_encode_document_no_header_for_plain_json():
    text, _ = encode_document({"name": "Alice", "age": 30}, source="json")
    assert not text.startswith(_CTX_LINE_PREFIX)


def test_roundtrip_auto_no_sidecar():
    text, _ = encode_document(MONGO_SHELL_DOC)  # auto-detects mongo_shell
    decoded = decode_document(text, target="json")
    assert decoded["_id"] == "69ca983fbf8c8953c43c2407"
    assert decoded["tags"] == ["forwarded", "drive"]
    assert decoded["real_time"] is True


def test_roundtrip_arrays_restored_without_sidecar():
    data = {"users": [{"name": "Alice"}, {"name": "Bob"}], "count": 2}
    text, _ = encode_document(data, source="json")
    decoded = decode_document(text, target="json")
    assert decoded == data


def test_explicit_context_overrides_embedded():
    text, _ = encode_document(MONGO_SHELL_DOC, source="mongo_shell")
    from jtoken import NormalizationContext
    empty_ctx = NormalizationContext()
    decoded = decode_document(text, target="json", context=empty_ctx)
    # With empty context, arrays come back as indexed dicts
    assert isinstance(decoded["tags"], dict)
