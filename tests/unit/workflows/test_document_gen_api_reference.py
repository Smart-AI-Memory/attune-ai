"""Unit tests for attune.workflows.document_gen.api_reference module.

Tests cover:
- APIReferenceMixin._extract_functions_from_source: AST-based extraction
- APIReferenceMixin._generate_api_section_for_function: LLM-based generation
- APIReferenceMixin._add_api_reference_sections: end-to-end integration

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.api_reference import APIReferenceMixin


class _FakeHost(APIReferenceMixin):
    """Minimal host for APIReferenceMixin testing."""

    def __init__(self) -> None:
        self._accumulated_cost: float = 0.0

    async def _call_llm(self, tier, system, user_msg, max_tokens=1000) -> tuple[str, int, int]:
        """Mock LLM call returning a formatted section."""
        return "### `test_func()`\n\n**Args:**\nNone", 50, 100

    def _track_cost(self, tier, input_tokens, output_tokens) -> tuple[float, bool]:
        """Mock cost tracker."""
        return 0.001, False


@pytest.fixture
def host() -> _FakeHost:
    """Create a host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _extract_functions_from_source
# ---------------------------------------------------------------------------


class TestExtractFunctionsFromSource:
    """Tests for APIReferenceMixin._extract_functions_from_source."""

    def test_extracts_public_function(self, host: _FakeHost) -> None:
        """Test extraction of a public function."""
        source = '''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello {name}"
'''
        funcs = host._extract_functions_from_source(source)
        assert len(funcs) == 1
        assert funcs[0]["name"] == "greet"
        assert funcs[0]["return_type"] == "str"
        assert funcs[0]["docstring"] == "Say hello."

    def test_skips_private_functions(self, host: _FakeHost) -> None:
        """Test that private functions (starting with _) are skipped."""
        source = """
def _private(): pass
def __dunder(): pass
def public(): pass
"""
        funcs = host._extract_functions_from_source(source)
        names = [f["name"] for f in funcs]
        assert "_private" not in names
        assert "__dunder" not in names
        assert "public" in names

    def test_extracts_arg_types(self, host: _FakeHost) -> None:
        """Test that argument types are extracted."""
        source = '''
def calculate(x: int, y: float) -> float:
    """Calculate something."""
    return x + y
'''
        funcs = host._extract_functions_from_source(source)
        args = funcs[0]["args"]
        assert len(args) == 2
        assert args[0]["name"] == "x"
        assert args[0]["type"] == "int"
        assert args[1]["name"] == "y"
        assert args[1]["type"] == "float"

    def test_no_type_annotation_defaults_to_any(self, host: _FakeHost) -> None:
        """Test that missing type annotations default to 'Any'."""
        source = """
def process(data):
    pass
"""
        funcs = host._extract_functions_from_source(source)
        assert funcs[0]["args"][0]["type"] == "Any"
        assert funcs[0]["return_type"] == "Any"

    def test_syntax_error_returns_empty(self, host: _FakeHost) -> None:
        """Test that syntax errors return empty list."""
        funcs = host._extract_functions_from_source("def broken(")
        assert funcs == []

    def test_no_functions_returns_empty(self, host: _FakeHost) -> None:
        """Test that source with no functions returns empty list."""
        funcs = host._extract_functions_from_source("x = 1\ny = 2\n")
        assert funcs == []

    def test_extracts_lineno(self, host: _FakeHost) -> None:
        """Test that line number is included."""
        source = """
x = 1

def func():
    pass
"""
        funcs = host._extract_functions_from_source(source)
        assert funcs[0]["lineno"] == 4


# ---------------------------------------------------------------------------
# _generate_api_section_for_function
# ---------------------------------------------------------------------------


class TestGenerateApiSection:
    """Tests for APIReferenceMixin._generate_api_section_for_function."""

    @pytest.mark.asyncio
    async def test_generates_section(self, host: _FakeHost) -> None:
        """Test that a section is generated for a function."""
        func_info = {
            "name": "greet",
            "args": [{"name": "name", "type": "str"}],
            "return_type": "str",
            "docstring": "Say hello.",
        }

        result = await host._generate_api_section_for_function(func_info, ModelTier.CHEAP)

        assert "test_func" in result or "greet" in result or "Args" in result

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, host: _FakeHost) -> None:
        """Test fallback when LLM call fails."""
        host._call_llm = AsyncMock(side_effect=RuntimeError("API error"))

        func_info = {
            "name": "calculate",
            "args": [{"name": "x", "type": "int"}],
            "return_type": "float",
            "docstring": "Do math.",
        }

        result = await host._generate_api_section_for_function(func_info, ModelTier.CHEAP)

        # Should return fallback format
        assert "calculate" in result
        assert "Args:" in result


# ---------------------------------------------------------------------------
# _add_api_reference_sections
# ---------------------------------------------------------------------------


class TestAddApiReferenceSections:
    """Tests for APIReferenceMixin._add_api_reference_sections."""

    @pytest.mark.asyncio
    async def test_appends_api_reference(self, host: _FakeHost) -> None:
        """Test that API reference section is appended to doc."""
        source = '''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello {name}"
'''
        result = await host._add_api_reference_sections(
            "# My Doc\n\nSome content.",
            source,
            ModelTier.CHEAP,
        )

        assert "## API Reference" in result
        assert "# My Doc" in result

    @pytest.mark.asyncio
    async def test_no_public_functions_returns_original(self, host: _FakeHost) -> None:
        """Test that doc is unchanged when no public functions exist."""
        source = "x = 1\n_private = 2\n"
        original = "# My Doc"

        result = await host._add_api_reference_sections(original, source, ModelTier.CHEAP)

        assert result == original
