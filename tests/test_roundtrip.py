import json

from jtoken import decode, denormalize, encode, encode_document, normalize


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
