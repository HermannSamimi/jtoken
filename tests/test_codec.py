import pytest

from jpack import JPackDecodeError, JPackEncodeError, decode, encode


class TestEncode:
    def test_string_value(self):
        assert encode({"name": "Alice"}) == "name: Alice"

    def test_int_value(self):
        assert encode({"age": 30}) == "age: 30"

    def test_float_value(self):
        assert encode({"score": 9.5}) == "score: 9.5"

    def test_bool_true(self):
        assert encode({"active": True}) == "active: true"

    def test_bool_false(self):
        assert encode({"active": False}) == "active: false"

    def test_none_single(self):
        assert encode({"x": None}) == "nulls: x"

    def test_none_multiple(self):
        result = encode({"a": None, "b": None})
        assert result == "nulls: a,b"

    def test_none_at_end(self):
        result = encode({"name": "Alice", "missing": None})
        lines = result.splitlines()
        assert lines[0] == "name: Alice"
        assert lines[-1] == "nulls: missing"

    def test_mixed(self):
        result = encode({"name": "Alice", "age": 30, "active": True, "x": None})
        lines = result.splitlines()
        assert "name: Alice" in lines
        assert "age: 30" in lines
        assert "active: true" in lines
        assert any(l.startswith("nulls:") for l in lines)

    def test_empty_dict(self):
        assert encode({}) == ""

    def test_reserved_key_raises(self):
        with pytest.raises(JPackEncodeError, match="reserved"):
            encode({"nulls": "something"})

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

    def test_bool_true(self):
        assert decode("active: true") == {"active": True}

    def test_bool_false(self):
        assert decode("active: false") == {"active": False}

    def test_bool_case_insensitive(self):
        assert decode("a: True")["a"] is True
        assert decode("b: FALSE")["b"] is False

    def test_null_single(self):
        assert decode("nulls: x") == {"x": None}

    def test_null_multiple(self):
        assert decode("nulls: a,b,c") == {"a": None, "b": None, "c": None}

    def test_null_with_spaces(self):
        assert decode("nulls: a, b") == {"a": None, "b": None}

    def test_multiline(self):
        text = "name: Alice\nage: 30\nactive: true"
        assert decode(text) == {"name": "Alice", "age": 30, "active": True}

    def test_empty_string(self):
        assert decode("") == {}

    def test_value_with_colon(self):
        assert decode("url: http://example.com") == {"url": "http://example.com"}

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

    def test_empty(self):
        assert decode(encode({})) == {}

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
