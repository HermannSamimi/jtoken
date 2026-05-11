import pytest

from jtoken import JPackDecodeError, JPackEncodeError, decode, encode


class TestEncode:
    def test_string_value(self):
        assert encode({"name": "Alice"}) == "name: Alice"

    def test_int_value(self):
        assert encode({"age": 30}) == "age: 30"

    def test_float_value(self):
        assert encode({"score": 9.5}) == "score: 9.5"

    # Booleans are now collapsed into summary lines
    def test_bool_true_collapsed(self):
        assert encode({"active": True}) == "trues: active"

    def test_bool_false_collapsed(self):
        assert encode({"active": False}) == "falses: active"

    def test_multiple_trues(self):
        result = encode({"a": True, "b": True})
        assert result == "trues: a,b"

    def test_multiple_falses(self):
        result = encode({"a": False, "b": False})
        assert result == "falses: a,b"

    def test_trues_and_falses_separate_lines(self):
        lines = encode({"a": True, "b": False}).splitlines()
        assert any(l.startswith("trues:") for l in lines)
        assert any(l.startswith("falses:") for l in lines)

    def test_none_single(self):
        assert encode({"x": None}) == "nulls: x"

    def test_none_multiple(self):
        assert encode({"a": None, "b": None}) == "nulls: a,b"

    def test_summary_lines_at_end(self):
        lines = encode({"name": "Alice", "ok": True, "missing": None}).splitlines()
        assert lines[0] == "name: Alice"
        # trues and nulls come after scalar values
        assert lines.index(next(l for l in lines if l.startswith("trues:"))) > 0
        assert lines.index(next(l for l in lines if l.startswith("nulls:"))) > 0

    def test_empty_dict(self):
        assert encode({}) == ""

    # Disambiguation: string values that look like numbers or booleans keep quotes
    def test_string_int_gets_quotes(self):
        assert encode({"zip": "90210"}) == 'zip: "90210"'

    def test_string_float_gets_quotes(self):
        assert encode({"val": "3.14"}) == 'val: "3.14"'

    def test_string_bool_gets_quotes(self):
        assert encode({"flag": "true"}) == 'flag: "true"'
        assert encode({"flag": "False"}) == 'flag: "False"'

    def test_empty_string_gets_quotes(self):
        assert encode({"x": ""}) == 'x: ""'

    def test_plain_string_no_quotes(self):
        assert encode({"city": "New York"}) == "city: New York"
        assert encode({"email": "a@b.com"}) == "email: a@b.com"

    def test_multiline_string_is_json_quoted(self):
        text = "line one\nline two"
        assert encode({"prompt": text}) == 'prompt: "line one\\nline two"'

    # Nested dicts
    def test_nested_dict_flat_notation(self):
        result = encode({"meta": {"verified": True}})
        assert "trues: meta.verified" in result

    def test_nested_null_collapsed(self):
        result = encode({"meta": {"score": None}})
        assert "nulls: meta.score" in result

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": 42}}}
        assert encode(data) == "a.b.c: 42"

    def test_reserved_key_raises(self):
        with pytest.raises(JPackEncodeError, match="reserved"):
            encode({"nulls": "something"})
        with pytest.raises(JPackEncodeError, match="reserved"):
            encode({"trues": "something"})
        with pytest.raises(JPackEncodeError, match="reserved"):
            encode({"falses": "something"})

    def test_dot_in_key_raises(self):
        with pytest.raises(JPackEncodeError, match="'.'"):
            encode({"a.b": "value"})

    def test_separator_in_key_raises(self):
        with pytest.raises(JPackEncodeError):
            encode({"a: b": "value"})

    def test_unsupported_type_raises(self):
        with pytest.raises(JPackEncodeError, match="Unsupported"):
            encode({"data": [1, 2, 3]})

    def test_non_dict_raises(self):
        with pytest.raises(JPackEncodeError, match="Expected dict"):
            encode("not a dict")  # type: ignore


class TestDecode:
    def test_string_value(self):
        assert decode("name: Alice") == {"name": "Alice"}

    def test_int_value(self):
        result = decode("age: 30")
        assert result == {"age": 30}
        assert isinstance(result["age"], int)

    def test_float_value(self):
        result = decode("score: 9.5")
        assert result == {"score": 9.5}
        assert isinstance(result["score"], float)

    def test_trues_line(self):
        assert decode("trues: active") == {"active": True}

    def test_falses_line(self):
        assert decode("falses: active") == {"active": False}

    def test_multiple_trues(self):
        assert decode("trues: a,b,c") == {"a": True, "b": True, "c": True}

    def test_multiple_falses(self):
        assert decode("falses: a,b,c") == {"a": False, "b": False, "c": False}

    # Backward compat — old inline format still decoded correctly
    def test_inline_true_compat(self):
        assert decode("active: true") == {"active": True}

    def test_inline_false_compat(self):
        assert decode("active: false") == {"active": False}

    def test_inline_bool_case_insensitive(self):
        assert decode("a: True")["a"] is True
        assert decode("b: FALSE")["b"] is False

    def test_null_line(self):
        assert decode("nulls: x,y") == {"x": None, "y": None}

    def test_quoted_string_stays_string(self):
        assert decode('zip: "90210"') == {"zip": "90210"}
        assert isinstance(decode('zip: "90210"')["zip"], str)

    def test_quoted_bool_string_stays_string(self):
        assert decode('flag: "true"') == {"flag": "true"}

    def test_quoted_empty_string(self):
        assert decode('x: ""') == {"x": ""}

    def test_multiline(self):
        text = "name: Alice\nage: 30\ntrues: active\nnulls: ref"
        assert decode(text) == {"name": "Alice", "age": 30, "active": True, "ref": None}

    def test_empty_string(self):
        assert decode("") == {}

    def test_url_value_safe(self):
        assert decode("url: http://example.com") == {"url": "http://example.com"}

    # Nested reconstruction via dot notation
    def test_dot_key_reconstructs_nested(self):
        assert decode("meta.score: 42") == {"meta": {"score": 42}}

    def test_deep_dot_key(self):
        assert decode("a.b.c: 42") == {"a": {"b": {"c": 42}}}

    def test_trues_with_dot_key(self):
        assert decode("trues: meta.verified") == {"meta": {"verified": True}}

    def test_nulls_with_dot_key(self):
        assert decode("nulls: meta.score") == {"meta": {"score": None}}

    def test_invalid_line_raises(self):
        with pytest.raises(JPackDecodeError, match="separator"):
            decode("no separator here")

    def test_non_string_raises(self):
        with pytest.raises(JPackDecodeError, match="Expected str"):
            decode(42)  # type: ignore


class TestRoundTrip:
    def test_basic(self):
        data = {"name": "Alice", "age": 30, "active": True, "score": 9.5}
        assert decode(encode(data)) == data

    def test_with_none(self):
        data = {"name": "Alice", "missing": None, "also_missing": None}
        assert decode(encode(data)) == data

    def test_booleans(self):
        data = {"a": True, "b": False, "c": True, "d": False}
        assert decode(encode(data)) == data

    def test_all_types(self):
        data = {
            "s": "hello world",
            "i": 42,
            "f": 3.14,
            "b_true": True,
            "b_false": False,
            "n": None,
        }
        assert decode(encode(data)) == data

    def test_string_that_looks_like_int(self):
        data = {"zip": "90210", "code": "007"}
        assert decode(encode(data)) == data

    def test_string_that_looks_like_bool(self):
        data = {"status": "true", "flag": "False"}
        assert decode(encode(data)) == data

    def test_empty_string(self):
        assert decode(encode({"tag": ""})) == {"tag": ""}

    def test_empty_dict(self):
        assert decode(encode({})) == {}

    def test_multiline_string_round_trip(self):
        data = {"prompt": "line one\nline two"}
        assert decode(encode(data)) == data

    def test_nested_dict(self):
        data = {"user": {"name": "Alice", "age": 30}}
        assert decode(encode(data)) == data

    def test_nested_booleans(self):
        data = {"meta": {"verified": True, "sponsored": False, "score": None}}
        assert decode(encode(data)) == data

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": {"d": 42, "e": True, "f": None}}}}
        assert decode(encode(data)) == data

    def test_mixed_nested_and_flat(self):
        data = {
            "title": "Engineer",
            "active": True,
            "ref": None,
            "meta": {"verified": True, "flagged": None, "score": 9.5},
        }
        assert decode(encode(data)) == data

    def test_real_world_nested_doc(self):
        data = {
            "title": "Senior Data Engineer (m/w/d)",
            "company": "Instaffo",
            "location": "Cologne, North Rhine-Westphalia, Germany",
            "date_posted": None,
            "job_type": None,
            "metadata": {
                "verified": True,
                "sponsored": False,
                "flagged": None,
                "priority": None,
                "archived": False,
                "source_details": {
                    "crawled": True,
                    "parsed": False,
                    "enriched": None,
                    "deduplicated": None,
                    "published": True,
                    "quality": {
                        "score": None,
                        "reviewed": False,
                        "auto_approved": True,
                        "flagged_duplicate": None,
                        "passed_filter": True,
                        "deep_check": {
                            "nlp_parsed": True,
                            "entity_extracted": None,
                            "salary_inferred": False,
                            "location_normalized": True,
                            "title_standardized": None,
                        },
                    },
                },
            },
        }
        assert decode(encode(data)) == data
