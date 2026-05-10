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
        assert encode({"a": None, "b": None}) == "nulls: a,b"

    def test_none_at_end(self):
        lines = encode({"name": "Alice", "missing": None}).splitlines()
        assert lines[0] == "name: Alice"
        assert lines[-1] == "nulls: missing"

    def test_empty_dict(self):
        assert encode({}) == ""

    # Disambiguation: string values that look like numbers or booleans keep quotes
    def test_string_int_gets_quotes(self):
        assert encode({"zip": "90210"}) == 'zip: "90210"'

    def test_string_float_gets_quotes(self):
        assert encode({"val": "3.14"}) == 'val: "3.14"'

    def test_string_bool_true_gets_quotes(self):
        assert encode({"flag": "true"}) == 'flag: "true"'

    def test_string_bool_false_gets_quotes(self):
        assert encode({"flag": "false"}) == 'flag: "false"'

    def test_string_bool_mixedcase_gets_quotes(self):
        assert encode({"flag": "True"}) == 'flag: "True"'

    def test_empty_string_gets_quotes(self):
        assert encode({"x": ""}) == 'x: ""'

    def test_plain_string_no_quotes(self):
        # Normal strings must NOT get quotes (that's the whole point)
        assert encode({"city": "New York"}) == "city: New York"
        assert encode({"email": "a@b.com"}) == "email: a@b.com"

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

    def test_quoted_string_stays_string(self):
        assert decode('zip: "90210"') == {"zip": "90210"}
        assert isinstance(decode('zip: "90210"')["zip"], str)

    def test_quoted_bool_string_stays_string(self):
        assert decode('flag: "true"') == {"flag": "true"}
        assert isinstance(decode('flag: "true"')["flag"], str)

    def test_quoted_empty_string(self):
        assert decode('x: ""') == {"x": ""}

    def test_multiline(self):
        text = "name: Alice\nage: 30\nactive: true"
        assert decode(text) == {"name": "Alice", "age": 30, "active": True}

    def test_empty_string(self):
        assert decode("") == {}

    def test_value_with_colon(self):
        # partition on first ": " only — URLs are safe
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

    def test_string_that_looks_like_int(self):
        data = {"zip": "90210", "code": "007"}
        assert decode(encode(data)) == data

    def test_string_that_looks_like_bool(self):
        data = {"status": "true", "flag": "False"}
        assert decode(encode(data)) == data

    def test_empty_string(self):
        data = {"tag": ""}
        assert decode(encode(data)) == data

    def test_json_like_payload(self):
        data = {
            "user": "alice",
            "age": 30,
            "premium": True,
            "score": 9.5,
            "referral": None,
            "last_login": None,
        }
        assert decode(encode(data)) == data
