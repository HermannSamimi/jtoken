import pytest

from jpack import TokenCountError, count_tokens

tiktoken = pytest.importorskip("tiktoken", reason="tiktoken not installed")


class TestCountTokensEstimate:
    def test_empty_dict(self):
        assert count_tokens({}, backend="estimate") == 0

    def test_empty_string(self):
        assert count_tokens("", backend="estimate") == 0

    def test_returns_int(self):
        result = count_tokens({"name": "Alice"}, backend="estimate")
        assert isinstance(result, int)
        assert result > 0

    def test_accepts_string(self):
        text = "name: Alice\nage: 30"
        result = count_tokens(text, backend="estimate")
        assert result > 0

    def test_accepts_dict(self):
        result = count_tokens({"name": "Alice", "age": 30}, backend="estimate")
        assert result > 0

    def test_larger_data_has_more_tokens(self):
        small = count_tokens({"a": "x"}, backend="estimate")
        large = count_tokens({"key": "a much longer value string here"}, backend="estimate")
        assert large > small


class TestCountTokensTiktoken:
    def test_basic(self):
        result = count_tokens({"name": "Alice"}, backend="tiktoken")
        assert isinstance(result, int)
        assert result > 0

    def test_accepts_string(self):
        result = count_tokens("name: Alice\nage: 30", backend="tiktoken")
        assert isinstance(result, int)
        assert result > 0

    def test_accepts_dict(self):
        result = count_tokens({"name": "Alice", "age": 30}, backend="tiktoken")
        assert isinstance(result, int)
        assert result > 0

    def test_default_encoding(self):
        # cl100k_base is the default — should work without specifying model
        result = count_tokens({"x": "hello"})
        assert result > 0

    def test_explicit_model_name(self):
        result = count_tokens({"x": "hello"}, model="gpt-4")
        assert result > 0

    def test_explicit_encoding_name(self):
        result = count_tokens({"x": "hello"}, model="cl100k_base")
        assert result > 0

    def test_unknown_model_raises(self):
        with pytest.raises(TokenCountError, match="Unknown tiktoken"):
            count_tokens({"x": "hello"}, model="not-a-real-model", backend="tiktoken")

    def test_larger_input_more_tokens(self):
        short = count_tokens("a: b", backend="tiktoken")
        long = count_tokens("name: Alice\nage: 30\nactive: true\nscore: 9.5", backend="tiktoken")
        assert long > short


class TestCountTokensAuto:
    def test_auto_returns_positive_int(self):
        result = count_tokens({"name": "Alice"}, backend="auto")
        assert isinstance(result, int)
        assert result > 0

    def test_tiktoken_and_auto_agree(self):
        data = {"name": "Alice", "age": 30}
        auto = count_tokens(data, backend="auto")
        explicit = count_tokens(data, backend="tiktoken")
        assert auto == explicit
