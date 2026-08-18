"""Unit tests for attune.workflows.document_gen.write_stage module.

Tests cover:
- WriteStageMixin._write: content generation from outline

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.write_stage import WriteStageMixin


class _FakeHost(WriteStageMixin):
    """Minimal host for write stage mixin testing."""

    def __init__(self) -> None:
        self.max_write_tokens: int = 16000
        self.chunked_generation: bool = True
        self.sections_per_chunk: int = 3
        self.section_focus: list[str] | None = None
        self._total_content_tokens: int = 0

    def _auto_scale_tokens(self, section_count: int) -> int:
        """Mock token scaling."""
        return max(16000, min(64000, section_count * 2000))

    async def _write_chunked(
        self, sections, outline, doc_type, audience, content, tier
    ) -> tuple[dict, int, int]:
        """Mock chunked write."""
        return (
            {
                "draft_document": "chunked doc",
                "chunked": True,
                "chunk_count": 2,
            },
            200,
            400,
        )

    async def _call_llm(self, tier, system, user_msg, max_tokens=16000) -> tuple[str, int, int]:
        """Mock LLM call."""
        return "Generated documentation content.", 100, 200

    def _parse_outline_sections(self, outline: str) -> list[str]:
        """Mock section parser."""
        return ["Section 1", "Section 2", "Section 3"]


@pytest.fixture
def host() -> _FakeHost:
    """Create a fresh host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _write stage
# ---------------------------------------------------------------------------


class TestWriteStage:
    """Tests for WriteStageMixin._write."""

    @pytest.mark.asyncio
    async def test_single_pass_write(self, host: _FakeHost) -> None:
        """Test single-pass write when chunking not needed."""
        # 3 sections, chunk threshold = 3*2 = 6, so no chunking
        host.sections_per_chunk = 3

        input_data = {
            "outline": "1. Intro\n2. Setup\n3. API",
            "doc_type": "general",
            "audience": "developers",
            "content_to_document": "def foo(): pass",
        }

        result, in_t, out_t = await host._write(input_data, ModelTier.CAPABLE)

        assert result["chunked"] is False
        assert result["draft_document"] == "Generated documentation content."
        assert result["doc_type"] == "general"
        assert host._total_content_tokens == 200

    @pytest.mark.asyncio
    async def test_chunked_write_triggered(self, host: _FakeHost) -> None:
        """Test that chunked write is triggered for large outlines."""
        host.sections_per_chunk = 1  # threshold = 1*2 = 2

        # 3 sections > 2 threshold
        host._parse_outline_sections = lambda outline: ["S1", "S2", "S3"]

        input_data = {
            "outline": "1. S1\n2. S2\n3. S3",
            "doc_type": "general",
            "audience": "devs",
            "content_to_document": "code",
        }

        result, _, _ = await host._write(input_data, ModelTier.CAPABLE)

        assert result["chunked"] is True
        assert result["draft_document"] == "chunked doc"

    @pytest.mark.asyncio
    async def test_section_focus_disables_chunking(self, host: _FakeHost) -> None:
        """Test that section_focus prevents chunking."""
        host.sections_per_chunk = 1  # would normally trigger chunking
        host.section_focus = ["Introduction"]

        # 3 sections but section_focus is set
        host._parse_outline_sections = lambda outline: ["S1", "S2", "S3"]

        input_data = {
            "outline": "1. S1\n2. S2\n3. S3",
            "doc_type": "general",
            "audience": "devs",
            "content_to_document": "code",
        }

        result, _, _ = await host._write(input_data, ModelTier.CAPABLE)

        # Should use single-pass due to section_focus
        assert result["chunked"] is False

    @pytest.mark.asyncio
    async def test_write_passes_source_code_through(self, host: _FakeHost) -> None:
        """Test that source_code is passed through in result."""
        input_data = {
            "outline": "1. Section",
            "doc_type": "api",
            "audience": "devs",
            "content_to_document": "def bar(): pass",
        }

        result, _, _ = await host._write(input_data, ModelTier.CHEAP)

        assert result["source_code"] == "def bar(): pass"

    @pytest.mark.asyncio
    async def test_write_auto_scales_tokens(self, host: _FakeHost) -> None:
        """Test that max_write_tokens is auto-scaled."""
        host._parse_outline_sections = lambda outline: [f"S{i}" for i in range(20)]

        input_data = {
            "outline": "lots of sections",
            "doc_type": "general",
            "audience": "devs",
            "content_to_document": "code",
        }

        await host._write(input_data, ModelTier.CAPABLE)

        assert host.max_write_tokens == 40000  # 20 * 2000


def _oversized_module(n_funcs: int = 40) -> str:
    """Python source well over the write budget whose skeleton fits:
    bulky bodies (sentinel constant 1000001), compact signatures."""
    body = "\n".join(f"    v{j} = {j} * 1000001" for j in range(6))
    funcs = [f"def func_{i:03d}(x: int) -> int:\n{body}\n    return x\n" for i in range(n_funcs)]
    funcs.append(f"def zz_tail_function(name: str) -> str:\n{body}\n    return name\n")
    return "\n".join(funcs)


class TestWriteSourceBudget:
    """Single-pass write: oversized source degrades to an AST skeleton
    in the prompt — the tail signature survives (the old [:5000] slice
    chopped it), bodies are stripped, and the pass-through
    source_code stays the full original."""

    @pytest.mark.asyncio
    async def test_oversized_source_skeleton_in_prompt(self) -> None:
        class _Capture(_FakeHost):
            def __init__(self) -> None:
                super().__init__()
                self.user_msg = ""

            async def _call_llm(self, tier, system, user_msg, max_tokens=16000):
                self.user_msg = user_msg
                return "Generated documentation content.", 100, 200

        host = _Capture()
        source = _oversized_module()
        result, _, _ = await host._write(
            {"outline": "1. A\n2. B\n3. C\n", "content_to_document": source},
            ModelTier.CAPABLE,
        )
        assert "def zz_tail_function(name: str) -> str:" in host.user_msg
        assert "1000001" not in host.user_msg
        assert result["source_code"] == source
