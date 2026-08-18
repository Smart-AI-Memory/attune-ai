"""Unit tests for attune.workflows.document_gen.chunked_generation module.

Tests cover:
- ChunkedGenerationMixin._write_chunked: chunked doc generation
- ChunkedGenerationMixin._polish_chunked: chunked polish stage
- ChunkedGenerationMixin._export_document: file export with validation
- ChunkedGenerationMixin._chunk_output_for_display: display chunking

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.chunked_generation import ChunkedGenerationMixin


class _FakeHost(ChunkedGenerationMixin):
    """Minimal host for chunked generation mixin testing."""

    def __init__(self) -> None:
        self.max_write_tokens: int = 16000
        self.sections_per_chunk: int = 3
        self.max_cost: float = 5.0
        self.graceful_degradation: bool = True
        self.export_path: Path | None = None
        self.max_display_chars: int = 45000
        self._accumulated_cost: float = 0.0
        self._total_content_tokens: int = 0
        self._partial_results: dict = {}

    async def _call_llm(self, tier, system, user_msg, max_tokens=8000) -> tuple[str, int, int]:
        """Mock LLM call returning generated content."""
        return "## Section Content\n\nGenerated documentation.", 100, 200

    def _track_cost(self, tier, input_tokens, output_tokens) -> tuple[float, bool]:
        """Mock cost tracker."""
        self._accumulated_cost += 0.01
        return 0.01, False

    async def _add_api_reference_sections(self, narrative_doc, source_code, tier) -> str:
        """Mock API reference addition."""
        return narrative_doc + "\n\n## API Reference\n"


@pytest.fixture
def host() -> _FakeHost:
    """Create a fresh host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _chunk_output_for_display
# ---------------------------------------------------------------------------


class TestChunkOutputForDisplay:
    """Tests for ChunkedGenerationMixin._chunk_output_for_display."""

    def test_small_content_single_chunk(self, host: _FakeHost) -> None:
        """Test that small content returns a single chunk."""
        host.max_display_chars = 1000
        chunks = host._chunk_output_for_display("small content")
        assert len(chunks) == 1
        assert chunks[0] == "small content"

    def test_large_content_split(self, host: _FakeHost) -> None:
        """Test that large content is split into multiple chunks."""
        host.max_display_chars = 50
        content = "## Section A\n\n" + "a" * 40 + "\n\n## Section B\n\n" + "b" * 40
        chunks = host._chunk_output_for_display(content)
        assert len(chunks) >= 2

    def test_chunk_prefix_included(self, host: _FakeHost) -> None:
        """Test that chunk prefix appears in output."""
        host.max_display_chars = 50
        content = "## S1\n\n" + "x" * 40 + "\n\n## S2\n\n" + "y" * 40
        chunks = host._chunk_output_for_display(content, chunk_prefix="DOC")
        for chunk in chunks:
            assert "DOC" in chunk

    def test_total_count_in_headers(self, host: _FakeHost) -> None:
        """Test that total count is correctly populated in chunk headers."""
        host.max_display_chars = 30
        content = "## A\n" + "a" * 30 + "\n## B\n" + "b" * 30
        chunks = host._chunk_output_for_display(content)
        total = len(chunks)
        for chunk in chunks:
            assert f"of {total}" in chunk


# ---------------------------------------------------------------------------
# _export_document
# ---------------------------------------------------------------------------


class TestExportDocument:
    """Tests for ChunkedGenerationMixin._export_document."""

    def test_export_disabled_returns_none(self, host: _FakeHost) -> None:
        """Test that export returns None when export_path is not set."""
        host.export_path = None
        doc_path, report_path = host._export_document("content", "api")
        assert doc_path is None
        assert report_path is None

    def test_export_creates_files(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test that export creates document and report files."""
        host.export_path = tmp_path / "exports"

        doc_path, report_path = host._export_document(
            "# Documentation\n\nContent here.",
            "api_reference",
            report="Report content",
        )

        assert doc_path is not None
        assert doc_path.exists()
        assert doc_path.read_text(encoding="utf-8") == "# Documentation\n\nContent here."

        assert report_path is not None
        assert report_path.exists()

    def test_export_no_report(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test export without report."""
        host.export_path = tmp_path / "out"

        doc_path, report_path = host._export_document("content", "general", report=None)

        assert doc_path is not None
        assert report_path is None

    def test_export_path_validation_error(self, host: _FakeHost, tmp_path: Path) -> None:
        """Test graceful handling of path validation errors."""
        host.export_path = tmp_path / "out"

        with patch(
            "attune.workflows.document_gen.chunked_generation._validate_file_path",
            side_effect=ValueError("bad path"),
        ):
            doc_path, report_path = host._export_document("content", "api")

        assert doc_path is None
        assert report_path is None


# ---------------------------------------------------------------------------
# _write_chunked
# ---------------------------------------------------------------------------


class TestWriteChunked:
    """Tests for ChunkedGenerationMixin._write_chunked."""

    @pytest.mark.asyncio
    async def test_basic_chunked_write(self, host: _FakeHost) -> None:
        """Test basic chunked writing."""
        sections = ["Introduction", "Setup", "API Reference", "Examples", "FAQ", "Appendix"]

        result, in_t, out_t = await host._write_chunked(
            sections=sections,
            outline="1. Intro\n2. Setup\n...",
            doc_type="general",
            audience="developers",
            content_to_document="def foo(): pass",
            tier=ModelTier.CAPABLE,
        )

        assert result["chunked"] is True
        assert result["chunk_count"] >= 2
        assert result["chunks_completed"] >= 1
        assert "draft_document" in result

    @pytest.mark.asyncio
    async def test_cost_limit_stops_early(self, host: _FakeHost) -> None:
        """Test that cost limit stops generation early."""
        host._track_cost = lambda tier, it, ot: (0.01, True)  # always stop

        sections = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]

        result, _, _ = await host._write_chunked(
            sections, "outline", "general", "devs", "code", ModelTier.CAPABLE
        )

        assert result["stopped_early"] is True
        assert result["chunks_completed"] == 1
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_llm_error_with_graceful_degradation(self, host: _FakeHost) -> None:
        """Test graceful degradation on LLM error."""
        host.graceful_degradation = True
        host._call_llm = AsyncMock(side_effect=RuntimeError("LLM down"))

        sections = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]

        result, _, _ = await host._write_chunked(
            sections, "outline", "general", "devs", "code", ModelTier.CAPABLE
        )

        assert result["stopped_early"] is True
        assert "warning" in result

    @pytest.mark.asyncio
    async def test_llm_error_without_graceful_degradation(self, host: _FakeHost) -> None:
        """Test that LLM error raises when degradation is disabled."""
        host.graceful_degradation = False
        host._call_llm = AsyncMock(side_effect=RuntimeError("LLM down"))

        sections = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]

        with pytest.raises(RuntimeError, match="LLM down"):
            await host._write_chunked(
                sections, "outline", "general", "devs", "code", ModelTier.CAPABLE
            )


# ---------------------------------------------------------------------------
# _polish_chunked
# ---------------------------------------------------------------------------


class TestPolishChunked:
    """Tests for ChunkedGenerationMixin._polish_chunked."""

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.document_gen.chunked_generation.format_doc_gen_report",
        return_value="formatted report",
    )
    async def test_basic_polish(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test basic chunked polish stage."""
        input_data = {
            "draft_document": "## Section A\n\nContent A\n\n## Section B\n\nContent B",
            "doc_type": "general",
            "audience": "developers",
            "source_code": "def foo(): pass",
        }

        result, in_t, out_t = await host._polish_chunked(input_data, ModelTier.CAPABLE)

        assert "document" in result
        assert result["polish_chunked"] is True
        assert "API Reference" in result["document"]

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.document_gen.chunked_generation.format_doc_gen_report",
        return_value="report",
    )
    async def test_polish_no_source_code(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test polish when no source code available."""
        input_data = {
            "draft_document": "## Section\n\nContent",
            "doc_type": "general",
            "audience": "devs",
        }

        result, _, _ = await host._polish_chunked(input_data, ModelTier.CAPABLE)

        assert "document" in result
        # No API reference added since no source code
        assert "API Reference" not in result["document"]

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.document_gen.chunked_generation.format_doc_gen_report",
        return_value="report",
    )
    async def test_polish_cost_limit_keeps_unpolished(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that cost limit adds remaining sections unpolished."""
        host._track_cost = lambda tier, it, ot: (0.01, True)  # always stop

        input_data = {
            "draft_document": "## A\n\nContent A\n\n## B\n\nContent B\n\n## C\n\nContent C",
            "doc_type": "general",
            "audience": "devs",
            "source_code": "",
        }

        result, _, _ = await host._polish_chunked(input_data, ModelTier.CAPABLE)

        # Document should still have content (polished + unpolished)
        assert len(result["document"]) > 0


def _oversized_module(n_funcs: int = 40) -> str:
    """Python source well over the chunk budget whose skeleton fits:
    bulky bodies (sentinel constant 1000001), compact signatures."""
    body = "\n".join(f"    v{j} = {j} * 1000001" for j in range(6))
    funcs = [f"def func_{i:03d}(x: int) -> int:\n{body}\n    return x\n" for i in range(n_funcs)]
    funcs.append(f"def zz_tail_function(name: str) -> str:\n{body}\n    return name\n")
    return "\n".join(funcs)


class TestChunkedSourceBudget:
    """Chunked write: oversized source degrades to an AST skeleton in
    each chunk prompt — the tail signature survives (the old [:3000]
    slice chopped it) and bodies are stripped."""

    @pytest.mark.asyncio
    async def test_oversized_source_skeleton_in_chunk_prompt(self) -> None:
        class _Capture(_FakeHost):
            def __init__(self) -> None:
                super().__init__()
                self.user_msgs: list[str] = []

            async def _call_llm(self, tier, system, user_msg, max_tokens=8000):
                self.user_msgs.append(user_msg)
                return "## Section Content\n\nGenerated documentation.", 100, 200

        host = _Capture()
        result, _, _ = await host._write_chunked(
            ["Intro", "API"],
            "1. Intro\n2. API\n",
            "api",
            "developers",
            _oversized_module(),
            ModelTier.CAPABLE,
        )
        assert host.user_msgs, "chunked write made no LLM calls"
        for msg in host.user_msgs:
            assert "def zz_tail_function(name: str) -> str:" in msg
            assert "1000001" not in msg
