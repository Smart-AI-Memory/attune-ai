"""Tests for attune_author.polish."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune_author.polish import (
    build_source_summary,
    polish_template,
)


class TestBuildSourceSummary:
    """Tests for build_source_summary()."""

    def test_builds_full_summary(self) -> None:
        """Test summary with classes, functions, and docstrings."""
        result = build_source_summary(
            public_classes=[
                {"name": "Foo", "doc": "Foo class", "file": "foo.py"},
            ],
            public_functions=[
                {"name": "bar", "doc": "bar function", "file": "bar.py"},
            ],
            module_docstrings=["First module.", "Second module."],
            file_count=5,
        )

        assert "Module purposes:" in result
        assert "First module." in result
        assert "Classes:" in result
        assert "Foo: Foo class" in result
        assert "Functions:" in result
        assert "bar(): bar function" in result
        assert "Total source files: 5" in result

    def test_empty_inputs(self) -> None:
        """Test summary with no source info."""
        result = build_source_summary(
            public_classes=[],
            public_functions=[],
            module_docstrings=[],
            file_count=0,
        )
        assert "Total source files: 0" in result

    def test_handles_missing_doc_field(self) -> None:
        """Test that missing 'doc' fields are handled."""
        result = build_source_summary(
            public_classes=[{"name": "Foo", "file": "f.py"}],
            public_functions=[{"name": "bar", "file": "b.py"}],
            module_docstrings=[],
            file_count=2,
        )
        assert "Foo" in result
        assert "bar" in result

    def test_truncates_long_lists(self) -> None:
        """Test that long lists are truncated."""
        many_classes = [{"name": f"Class{i}", "doc": "", "file": "f.py"} for i in range(20)]
        result = build_source_summary(
            public_classes=many_classes,
            public_functions=[],
            module_docstrings=[],
            file_count=20,
        )
        # Should only include first 10
        assert "Class0" in result
        assert "Class9" in result
        assert "Class15" not in result


class TestPolishTemplate:
    """Tests for polish_template()."""

    def test_returns_original_on_no_api_key(self) -> None:
        """Test fallback to original when API key missing."""
        with patch.dict("os.environ", {}, clear=True):
            content = "# Test\nOriginal content."
            result = polish_template(content, "test", "summary")
            assert result == content

    def test_returns_original_on_llm_error(self) -> None:
        """Test fallback to original when LLM call fails."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("attune_author.polish._call_llm") as mock_call:
                mock_call.side_effect = RuntimeError("API down")
                content = "# Test\nOriginal."
                result = polish_template(content, "test", "summary")
                assert result == content

    def test_returns_polished_on_success(self) -> None:
        """Test successful polish returns LLM output."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("attune_author.polish._call_llm") as mock_call:
                mock_call.return_value = "# Test\nPolished content."
                result = polish_template("orig", "test", "summary")
                assert result == "# Test\nPolished content."

    def test_call_llm_uses_anthropic_client(self) -> None:
        """Test that _call_llm builds and uses an Anthropic client."""
        from attune_author.polish import _call_llm

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="polished output")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = _call_llm("content", "feature", "summary")

        assert result == "polished output"
        mock_client.messages.create.assert_called_once()

    def test_call_llm_raises_without_key(self) -> None:
        """Test that _call_llm raises without API key."""
        import pytest

        from attune_author.polish import _call_llm

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                _call_llm("content", "feature", "summary")
