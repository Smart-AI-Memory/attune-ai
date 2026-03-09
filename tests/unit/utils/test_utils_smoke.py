"""Smoke tests for utils.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.utils

        assert attune.utils is not None

    def test_token_functions_import(self) -> None:
        """Test that token utility functions import."""
        from attune.utils import count_message_tokens, count_tokens, estimate_cost

        assert count_tokens is not None
        assert count_message_tokens is not None
        assert estimate_cost is not None


@pytest.mark.unit
class TestTokenCounting:
    """Verify token counting functions work."""

    def test_count_tokens_empty_string(self) -> None:
        """Test count_tokens returns 0 for empty string."""
        from attune.utils import count_tokens

        assert count_tokens("") == 0

    def test_count_tokens_nonempty(self) -> None:
        """Test count_tokens returns positive for text."""
        from attune.utils import count_tokens

        result = count_tokens("Hello, world!")
        assert result > 0

    def test_count_message_tokens_basic(self) -> None:
        """Test count_message_tokens with simple messages."""
        from attune.utils import count_message_tokens

        messages = [{"role": "user", "content": "Hello"}]
        result = count_message_tokens(messages)
        assert isinstance(result, dict)
        assert "total" in result or "input_tokens" in result or len(result) > 0

    def test_estimate_cost_returns_float(self) -> None:
        """Test estimate_cost returns a float."""
        from attune.utils import estimate_cost

        cost = estimate_cost(input_tokens=1000, output_tokens=500)
        assert isinstance(cost, float)
        assert cost >= 0.0
