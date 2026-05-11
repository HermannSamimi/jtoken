import pytest

from jtoken import TokenSavings, count_tokens, token_savings

tiktoken = pytest.importorskip("tiktoken", reason="tiktoken not installed")

_SAMPLE = {"name": "Alice", "age": 30, "active": True, "score": 9.5, "ref": None}


class TestCountTokens:
    def test_returns_positive_int_for_dict(self):
        n = count_tokens(_SAMPLE)
        assert isinstance(n, int) and n > 0

    def test_returns_zero_for_empty_dict(self):
        assert count_tokens({}) == 0

    def test_accepts_jtoken_string(self):
        import jtoken
        text = jtoken.encode(_SAMPLE)
        assert count_tokens(text) == count_tokens(_SAMPLE)

    def test_estimate_backend(self):
        n = count_tokens(_SAMPLE, backend="estimate")
        assert isinstance(n, int) and n > 0

    def test_tiktoken_backend(self):
        n = count_tokens(_SAMPLE, backend="tiktoken")
        assert isinstance(n, int) and n > 0

    def test_auto_matches_tiktoken(self):
        assert count_tokens(_SAMPLE, backend="auto") == count_tokens(_SAMPLE, backend="tiktoken")

    def test_model_name(self):
        assert count_tokens(_SAMPLE, model="gpt-4") > 0

    def test_encoding_name(self):
        assert count_tokens(_SAMPLE, model="cl100k_base") > 0


class TestTokenSavings:
    def test_returns_token_savings(self):
        result = token_savings(_SAMPLE)
        assert isinstance(result, TokenSavings)

    def test_jtoken_uses_fewer_tokens_than_json(self):
        result = token_savings(_SAMPLE)
        assert result.jtoken_tokens < result.json_tokens

    def test_saved_is_positive(self):
        result = token_savings(_SAMPLE)
        assert result.saved > 0

    def test_percent_between_0_and_100(self):
        result = token_savings(_SAMPLE)
        assert 0 < result.percent < 100

    def test_savings_meaningful(self):
        # We claim ~30% — verify real savings are at least 10% for a typical payload
        result = token_savings(_SAMPLE)
        assert result.percent >= 10

    def test_accepts_jtoken_string(self):
        import jtoken
        text = jtoken.encode(_SAMPLE)
        result = token_savings(text)
        assert isinstance(result, TokenSavings)
        assert result.saved > 0

    def test_str_representation(self):
        result = token_savings(_SAMPLE)
        s = str(result)
        assert "jtoken:" in s
        assert "json:" in s
        assert "saved:" in s

    def test_estimate_backend(self):
        result = token_savings(_SAMPLE, backend="estimate")
        assert result.saved > 0

    def test_empty_dict(self):
        result = token_savings({})
        assert result.jtoken_tokens == 0
        assert result.json_tokens >= 0
