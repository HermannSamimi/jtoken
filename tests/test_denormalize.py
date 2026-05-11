import json

from jtoken import denormalize, normalize, render_output


MONGO_SHELL_DOC = """
{
    "_id" : ObjectId("69ca983fbf8c8953c43c2407"),
    "day" : ISODate("2026-02-12T00:00:00.000+0000"),
    "tags" : [
        "forwarded",
        "drive"
    ]
}
"""


class TestDenormalizeMongo:
    def test_mongo_extended_output(self):
        normalized, context = normalize(MONGO_SHELL_DOC, source="mongo_shell")
        restored = denormalize(normalized, target="mongo_extended", context=context)
        assert restored["_id"] == {"$oid": "69ca983fbf8c8953c43c2407"}
        assert restored["day"] == {"$date": "2026-02-12T00:00:00.000+0000"}
        assert restored["tags"] == ["forwarded", "drive"]

    def test_mongo_shell_render(self):
        normalized, context = normalize(MONGO_SHELL_DOC, source="mongo_shell")
        restored = denormalize(normalized, target="mongo_shell", context=context)
        rendered = render_output(restored, target="mongo_shell")
        assert 'ObjectId("69ca983fbf8c8953c43c2407")' in rendered
        assert 'ISODate("2026-02-12T00:00:00.000+0000")' in rendered
        assert '"forwarded"' in rendered


class TestDenormalizeElastic:
    def test_elastic_hit_output(self):
        hit = {
            "_index": "logs-example",
            "_id": "hit-1",
            "_version": 1,
            "_source": {
                "user": {"name": "alice"},
                "tags": ["forwarded"],
                "active": True,
            },
            "fields": {
                "user.name": ["alice"],
                "tags": ["forwarded"],
                "active": [True],
            },
        }
        normalized, context = normalize(hit, source="elastic_hit")
        restored = denormalize(normalized, target="elastic_hit", context=context)
        assert restored["_index"] == "logs-example"
        assert restored["_source"]["user"]["name"] == "alice"
        assert restored["fields"]["user.name"] == ["alice"]
        assert restored["fields"]["tags"] == ["forwarded"]
