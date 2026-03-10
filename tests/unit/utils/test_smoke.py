"""Smoke tests for attune.utils module."""


class TestUtilsImports:
    """Verify the utils package exports are importable."""

    def test_import_package(self):
        """Test that the utils package imports cleanly."""
        from attune.utils import count_message_tokens, count_tokens, estimate_cost

        assert count_tokens is not None
        assert count_message_tokens is not None
        assert estimate_cost is not None

    def test_count_tokens_empty_string(self):
        """Test count_tokens returns 0 for empty string."""
        from attune.utils.tokens import count_tokens

        assert count_tokens("") == 0

    def test_count_tokens_heuristic_fallback(self):
        """Test heuristic fallback for token counting."""
        from attune.utils.tokens import _count_tokens_heuristic

        assert _count_tokens_heuristic("") == 0
        # ~4 chars per token
        result = _count_tokens_heuristic("Hello world test")
        assert result > 0

    def test_token_count_dataclass(self):
        """Test TokenCount dataclass."""
        from attune.utils.tokens import TokenCount

        tc = TokenCount(tokens=42, method="heuristic", model=None)
        assert tc.tokens == 42
        assert tc.method == "heuristic"
