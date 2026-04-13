"""Unit tests for attune.help.polish module.

Tests cover:
- polish_template: graceful fallback on LLM failure
- _call_llm: API key check, Anthropic SDK call, empty response
- build_source_summary: formatting with all combos of inputs

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from attune.help.polish import (
    _call_llm,
    build_source_summary,
    polish_template,
)

# -- Fixtures --------------------------------------------------------


@dataclass
class _FakeTextBlock:
    text: str


@dataclass
class _FakeResponse:
    content: list[Any]


# -- polish_template -------------------------------------------------


class TestPolishTemplate:
    """Tests for polish_template()."""

    def test_returns_polished_content_on_success(self) -> None:
        """Polished content returned when LLM call succeeds."""
        with patch(
            "attune.help.polish._call_llm",
            return_value="polished output",
        ):
            result = polish_template("raw", "feat", "summary")
        assert result == "polished output"

    def test_returns_original_on_llm_failure(self) -> None:
        """Falls back to original content when LLM raises."""
        with patch(
            "attune.help.polish._call_llm",
            side_effect=RuntimeError("no key"),
        ):
            result = polish_template("raw content", "feat", "summary")
        assert result == "raw content"

    def test_returns_original_on_unexpected_error(self) -> None:
        """Falls back on any exception type (broad catch)."""
        with patch(
            "attune.help.polish._call_llm",
            side_effect=ValueError("unexpected"),
        ):
            result = polish_template("raw content", "feat", "summary")
        assert result == "raw content"


# -- _call_llm -------------------------------------------------------


class TestCallLlm:
    """Tests for _call_llm()."""

    def test_raises_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RuntimeError when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
            _call_llm("content", "feat", "summary")

    def test_calls_anthropic_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sends correct params to Anthropic SDK."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _FakeResponse(
            content=[_FakeTextBlock(text="polished")]
        )

        # Anthropic is imported lazily inside _call_llm — mock via sys.modules
        mock_anthropic = types.ModuleType("anthropic")
        mock_anthropic.Anthropic = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = _call_llm("content", "my-feature", "source info")

        assert result == "polished\n"
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 4096
        assert "my-feature" in call_kwargs["messages"][0]["content"]

    def test_returns_original_on_empty_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns original content when response.content is empty."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _FakeResponse(content=[])

        mock_anthropic = types.ModuleType("anthropic")
        mock_anthropic.Anthropic = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = _call_llm("original", "feat", "summary")

        assert result == "original"

    def test_appends_trailing_newline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensures LLM output ends with a trailing newline."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _FakeResponse(
            content=[_FakeTextBlock(text="polished content")]
        )

        mock_anthropic = types.ModuleType("anthropic")
        mock_anthropic.Anthropic = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = _call_llm("content", "feat", "summary")

        assert result.endswith("\n")

    def test_no_double_trailing_newline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Does not double-add newline when LLM already includes one."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # pragma: allowlist secret

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _FakeResponse(
            content=[_FakeTextBlock(text="polished\n")]
        )

        mock_anthropic = types.ModuleType("anthropic")
        mock_anthropic.Anthropic = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = _call_llm("content", "feat", "summary")

        assert result == "polished\n"


# -- build_source_summary -------------------------------------------


class TestBuildSourceSummary:
    """Tests for build_source_summary()."""

    def test_all_sections_present(self) -> None:
        """All sections rendered when all inputs provided."""
        result = build_source_summary(
            public_classes=[{"name": "Foo", "doc": "Does foo"}],
            public_functions=[{"name": "bar", "doc": "Does bar"}],
            module_docstrings=["Module summary"],
            file_count=5,
        )
        assert "Module purposes:" in result
        assert "Module summary" in result
        assert "Classes:" in result
        assert "Foo: Does foo" in result
        assert "Functions:" in result
        assert "bar(): Does bar" in result
        assert "Total source files: 5" in result

    def test_empty_inputs(self) -> None:
        """Only file count when all lists empty."""
        result = build_source_summary([], [], [], 0)
        assert result == "Total source files: 0"

    def test_class_without_doc(self) -> None:
        """Class entry renders name only when doc missing."""
        result = build_source_summary(
            public_classes=[{"name": "Bare"}],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
        )
        assert "  - Bare" in result
        assert "Bare:" not in result

    def test_function_without_doc(self) -> None:
        """Function entry renders name() only when doc missing."""
        result = build_source_summary(
            public_classes=[],
            public_functions=[{"name": "baz"}],
            module_docstrings=[],
            file_count=1,
        )
        assert "  - baz()" in result
        assert "baz():" not in result

    def test_truncates_long_lists(self) -> None:
        """Limits module_docstrings to 5 and classes/functions to 10."""
        result = build_source_summary(
            public_classes=[{"name": f"C{i}"} for i in range(15)],
            public_functions=[{"name": f"f{i}"} for i in range(15)],
            module_docstrings=[f"doc{i}" for i in range(8)],
            file_count=100,
        )
        # 5 docstrings max
        assert "doc4" in result
        assert "doc5" not in result
        # 10 classes max
        assert "C9" in result
        assert "C10" not in result
        # 10 functions max
        assert "f9" in result
        assert "f10" not in result

    def test_class_with_empty_doc_string(self) -> None:
        """Class with empty string doc renders name only."""
        result = build_source_summary(
            public_classes=[{"name": "Cls", "doc": ""}],
            public_functions=[],
            module_docstrings=[],
            file_count=1,
        )
        assert "  - Cls" in result
        assert "Cls:" not in result
