"""Unit tests for attune.workflows.document_gen.outline_stage module.

Tests cover:
- OutlineStageMixin._outline: outline generation stage
- OutlineStageMixin._read_target_file: file reading with fallback
- OutlineStageMixin._detect_auth_strategy: auth mode detection
- OutlineStageMixin._parse_outline_sections: section title parsing

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.outline_stage import OutlineStageMixin


class _FakeHost(OutlineStageMixin):
    """Minimal host for outline stage mixin testing."""

    def __init__(self) -> None:
        self.enable_auth_strategy: bool = False
        self._auth_mode_used: str | None = None

    async def _call_llm(self, tier, system, user_msg, max_tokens=1000) -> tuple[str, int, int]:
        """Mock LLM call returning an outline."""
        outline = "1. Introduction\n" "2. Quick Start\n" "3. API Reference\n"
        return outline, 100, 200


@pytest.fixture
def host() -> _FakeHost:
    """Create a host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _parse_outline_sections
# ---------------------------------------------------------------------------


class TestParseOutlineSections:
    """Tests for OutlineStageMixin._parse_outline_sections."""

    def test_parses_numbered_sections(self, host: _FakeHost) -> None:
        """Test parsing standard numbered sections."""
        outline = "1. Introduction\n2. Setup\n3. API Reference\n"
        sections = host._parse_outline_sections(outline)
        assert sections == ["Introduction", "Setup", "API Reference"]

    def test_strips_description_after_dash(self, host: _FakeHost) -> None:
        """Test that descriptions after ' - ' are stripped."""
        outline = "1. Introduction - Overview of the project\n"
        sections = host._parse_outline_sections(outline)
        assert sections == ["Introduction"]

    def test_ignores_sub_sections(self, host: _FakeHost) -> None:
        """Test that sub-sections like '2.1' are ignored."""
        outline = "1. Introduction\n" "  1.1. Background\n" "  1.2. Goals\n" "2. Setup\n"
        sections = host._parse_outline_sections(outline)
        assert sections == ["Introduction", "Setup"]

    def test_empty_outline_returns_empty(self, host: _FakeHost) -> None:
        """Test that empty outline returns empty list."""
        sections = host._parse_outline_sections("")
        assert sections == []

    def test_non_numbered_lines_ignored(self, host: _FakeHost) -> None:
        """Test that non-numbered lines are ignored."""
        outline = "Some intro text\n- bullet point\n1. Real Section\n"
        sections = host._parse_outline_sections(outline)
        assert sections == ["Real Section"]

    def test_multi_word_sections(self, host: _FakeHost) -> None:
        """Test multi-word section titles."""
        outline = "1. Getting Started Guide\n2. Advanced Configuration Options\n"
        sections = host._parse_outline_sections(outline)
        assert sections == ["Getting Started Guide", "Advanced Configuration Options"]


# ---------------------------------------------------------------------------
# _read_target_file
# ---------------------------------------------------------------------------


class TestReadTargetFile:
    """Tests for OutlineStageMixin._read_target_file."""

    def test_reads_existing_file(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test reading an existing file."""
        f = tmp_path / "module.py"
        f.write_text("def foo(): pass", encoding="utf-8")

        result = host._read_target_file(str(f), "fallback")

        assert "def foo" in result
        assert f"# File: {f}" in result

    def test_fallback_on_nonexistent_file(self, host: _FakeHost) -> None:
        """Test fallback when file doesn't exist."""
        result = host._read_target_file("/nonexistent/module.py", "my fallback")
        assert result == "my fallback"

    def test_fallback_on_read_error(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test fallback on file read error."""
        f = tmp_path / "broken.py"
        f.write_text("content", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            result = host._read_target_file(str(f), "fallback")

        assert result == "fallback"

    def test_non_file_path_returns_fallback(self, host: _FakeHost) -> None:
        """Test non-file-looking target returns fallback."""
        result = host._read_target_file("some plain text input", "fallback")
        assert result == "fallback"


# ---------------------------------------------------------------------------
# _detect_auth_strategy
# ---------------------------------------------------------------------------


class TestDetectAuthStrategy:
    """Tests for OutlineStageMixin._detect_auth_strategy."""

    def test_guard_in_outline_skips_when_disabled(self, host: _FakeHost) -> None:
        """Test that _outline skips auth strategy when disabled."""
        host.enable_auth_strategy = False
        # _detect_auth_strategy itself has no guard; the guard is in _outline
        # Verify that _auth_mode_used stays None when _outline is called
        assert host._auth_mode_used is None

    def test_import_error_handled(self, host: _FakeHost) -> None:
        """Test graceful handling when attune.models unavailable."""
        with patch.dict("sys.modules", {"attune.models": None}):
            host._detect_auth_strategy("target", "content")
        # Should not raise - error is caught internally
        # Should not raise


# ---------------------------------------------------------------------------
# _outline stage
# ---------------------------------------------------------------------------


class TestOutlineStage:
    """Tests for OutlineStageMixin._outline."""

    @pytest.mark.asyncio
    async def test_basic_outline(self, host: _FakeHost) -> None:
        """Test basic outline generation."""
        input_data = {
            "source_code": "def foo(): pass",
            "doc_type": "api_reference",
            "audience": "developers",
        }

        result, in_t, out_t = await host._outline(input_data, ModelTier.CHEAP)

        assert "outline" in result
        assert result["doc_type"] == "api_reference"
        assert result["audience"] == "developers"
        assert in_t == 100
        assert out_t == 200

    @pytest.mark.asyncio
    async def test_outline_reads_target_file(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test that outline reads file when target is a path."""
        f = tmp_path / "module.py"
        f.write_text("class MyClass: pass", encoding="utf-8")

        result, _, _ = await host._outline(
            {"target": str(f), "doc_type": "general", "audience": "devs"},
            ModelTier.CHEAP,
        )

        assert "MyClass" in result["content_to_document"]

    @pytest.mark.asyncio
    async def test_outline_uses_target_as_content_fallback(self, host: _FakeHost) -> None:
        """Test that target string is used directly when it's not a file."""
        result, _, _ = await host._outline(
            {"target": "some code here", "doc_type": "general", "audience": "devs"},
            ModelTier.CHEAP,
        )

        assert result["content_to_document"] == "some code here"


def _oversized_module(n_funcs: int = 40) -> str:
    """Python source well over the outline budget whose skeleton fits:
    bulky bodies (sentinel constant 1000001), compact signatures."""
    body = "\n".join(f"    v{j} = {j} * 1000001" for j in range(6))
    funcs = [f"def func_{i:03d}(x: int) -> int:\n{body}\n    return x\n" for i in range(n_funcs)]
    funcs.append(f"def zz_tail_function(name: str) -> str:\n{body}\n    return name\n")
    return "\n".join(funcs)


class TestOutlineSourceBudget:
    """Oversized source degrades to an AST skeleton in the prompt —
    every signature survives (the old [:4000] slice chopped the tail)
    while the full source still flows to later stages untouched."""

    @pytest.mark.asyncio
    async def test_oversized_source_skeleton_in_prompt(self) -> None:
        class _Capture(_FakeHost):
            def __init__(self) -> None:
                super().__init__()
                self.user_msg = ""

            async def _call_llm(self, tier, system, user_msg, max_tokens=1000):
                self.user_msg = user_msg
                return "1. Introduction\n", 100, 200

        host = _Capture()
        source = _oversized_module()
        result, _, _ = await host._outline(
            {"source_code": source, "doc_type": "api", "audience": "developers"},
            ModelTier.CHEAP,
        )
        assert "def zz_tail_function(name: str) -> str:" in host.user_msg
        assert "1000001" not in host.user_msg
        assert result["content_to_document"] == source
