import json

import pytest

from jtoken import NormalizationContext, normalize, parse_input
from jtoken.exceptions import NormalizationError


MONGO_SHELL_DOC = """
{
    "_id" : ObjectId("69ca983fbf8c8953c43c2407"),
    "influencer" : "alice@example.com",
    "day" : ISODate("2026-02-12T00:00:00.000+0000"),
    "threshold" : 1.45,
    "buckets" : [
        {
            "bucket_time" : ISODate("2026-02-12T17:45:00.000+0000"),
            "count" : NumberInt(1)
        }
    ],
    "tags" : [
        "forwarded",
        "google_workspace-drive"
    ]
}
"""

MONGO_EXTENDED_DOC = {
    "_id": {"$oid": "69cba8395d4a83d479e4ebf5"},
    "learn_window_days": {"$numberInt": "60"},
    "severity_score": {"$numberInt": "96"},
    "creationTimestamp": {"$date": "2026-03-31T10:55:53.070+0000"},
    "slack_channel": None,
    "real_time": True,
}

ELASTIC_HIT = {
    "_index": "logs-example",
    "_id": "hit-1",
    "_version": 1,
    "_source": {
        "user": {"name": "alice", "email": "alice@example.com"},
        "tags": ["forwarded", "drive"],
        "event": {"action": "trash", "category": ["file"]},
        "active": True,
    },
    "fields": {
        "user.name": ["alice"],
        "user.email": ["alice@example.com"],
        "tags": ["forwarded", "drive"],
        "event.action": ["trash"],
        "event.category": ["file"],
        "active": [True],
        "extra.only.in.fields": ["value"],
    },
}


class TestParseInput:
    def test_parse_json(self):
        assert parse_input('{"a": 1}', source="json") == {"a": 1}

    def test_parse_json_array(self):
        assert parse_input('[{"a": 1}]', source="json") == [{"a": 1}]

    def test_parse_json_array_auto(self):
        assert parse_input('[{"a": 1}]', source="auto") == [{"a": 1}]

    def test_parse_mongo_shell(self):
        parsed = parse_input(MONGO_SHELL_DOC, source="mongo_shell")
        assert parsed["_id"]["$oid"] == "69ca983fbf8c8953c43c2407"


class TestNormalizeMongo:
    def test_mongo_shell_types_and_lists(self):
        normalized, context = normalize(MONGO_SHELL_DOC, source="mongo_shell")
        assert normalized["influencer"] == "alice@example.com"
        assert normalized["_id"] == "69ca983fbf8c8953c43c2407"
        assert context.typed_values["_id"] == "object_id"
        assert context.typed_values["day"] == "datetime"
        assert "tags" in context.lists
        assert normalized["tags"]["0"] == "forwarded"
        assert normalized["buckets"]["0"]["count"] == 1

    def test_mongo_extended_types(self):
        normalized, context = normalize(MONGO_EXTENDED_DOC, source="mongo_extended")
        assert normalized["_id"] == "69cba8395d4a83d479e4ebf5"
        assert normalized["learn_window_days"] == 60
        assert normalized["creationTimestamp"] == "2026-03-31T10:55:53.070+0000"
        assert context.typed_values["_id"] == "object_id"
        assert context.typed_values["creationTimestamp"] == "datetime"


class TestNormalizeElastic:
    def test_elastic_hit_prefers_source_and_unwraps_fields(self):
        normalized, context = normalize(ELASTIC_HIT, source="elastic_hit")
        assert normalized["user"]["name"] == "alice"
        assert normalized["tags"]["0"] == "forwarded"
        assert normalized["event"]["category"]["0"] == "file"
        assert context.elastic is not None
        assert context.elastic["envelope"]["_index"] == "logs-example"
        assert "user.name" in context.elastic["skipped_fields"]
        assert normalized["extra"]["only"]["in"]["fields"] == "value"

    def test_elastic_source(self):
        normalized, _ = normalize({"_source": {"a": 1}}, source="elastic_source")
        assert normalized == {"a": 1}


class TestNormalizationContext:
    def test_round_trip_dict(self):
        _, context = normalize({"tags": ["a"]}, source="json")
        restored = NormalizationContext.from_dict(context.to_dict())
        assert restored.lists == context.lists


class TestDottedKeys:
    def test_nested_key_with_dot_is_sanitized(self):
        data = {
            "query": {
                "match_phrase": {
                    "event.action": "download",
                }
            }
        }
        normalized, context = normalize(data, source="json")
        assert "event__DOT__action" in normalized["query"]["match_phrase"]
        assert context.dotted_keys


class TestNormalizeErrors:
    def test_unsupported_type_raises(self):
        with pytest.raises(NormalizationError):
            normalize({"bad": object()}, source="json")


class TestNormalizeJsonArrays:
    def test_single_object_array_is_unwrapped(self):
        normalized, context = normalize('[{"QUERY_ID": "q-1", "ROWS_DELETED": 0}]', source="json")
        assert normalized["QUERY_ID"] == "q-1"
        assert normalized["ROWS_DELETED"] == 0
        assert "" not in context.lists

    def test_single_object_array_auto(self):
        normalized, _ = normalize('[{"a": 1}]', source="auto")
        assert normalized == {"a": 1}

    def test_multi_object_array_is_indexed(self):
        normalized, context = normalize('[{"a": 1}, {"b": 2}]', source="json")
        assert normalized["0"]["a"] == 1
        assert normalized["1"]["b"] == 2
        assert "" in context.lists

    def test_primitive_array_is_indexed(self):
        normalized, context = normalize('["a", "b"]', source="json")
        assert normalized["0"] == "a"
        assert normalized["1"] == "b"
        assert "" in context.lists
