"""Unit tests for attune.workflows.document_gen.polish_stage module.

Tests cover:
- PolishStageMixin._polish: main polish stage with chunked vs single path
- PolishStageMixin._build_polish_prompts: XML vs legacy prompt construction
- PolishStageMixin._execute_polish_llm: executor vs legacy fallback
- PolishStageMixin._build_polish_result: result dict assembly

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.polish_stage import PolishStageMixin


class _FakeHost(PolishStageMixin):
    """Minimal host for polish stage mixin testing."""

    def __init__(self) -> None:
        self.max_write_tokens: int = 16000
        self._accumulated_cost: float = 0.0
        self._auth_mode_used: str | None = None
        self.export_path: Path | None = None
        self._executor = None
        self._api_key: str | None = None
        self._xml_enabled: bool = False

    def _is_xml_enabled(self) -> bool:
        """Check if XML is enabled."""
        return self._xml_enabled

    def _render_xml_prompt(self, **kwargs) -> str:
        """Return mock XML prompt."""
        return "xml prompt"

    def _parse_xml_response(self, response: str) -> dict:
        """Parse XML response (mock)."""
        return {}

    async def _call_llm(self, tier, system, user_msg, max_tokens=20000) -> tuple[str, int, int]:
        """Mock LLM call."""
        return "Polished document content.", 100, 200

    async def run_step_with_executor(self, step, prompt, system=None):
        """Mock executor."""
        from attune.workflows.executor_mixin import StepResult

        return StepResult(
            content="Executor polished content.",
            input_tokens=50,
            output_tokens=100,
            cost=0.01,
        )

    async def _polish_chunked(self, input_data, tier):
        """Mock chunked polish."""
        return {"document": "chunked polished", "doc_type": "general"}, 100, 200

    async def _add_api_reference_sections(self, narrative_doc, source_code, tier):
        """Mock API reference addition."""
        return narrative_doc + "\n\n## API Ref"

    def _export_document(self, document, doc_type, report=None):
        """Mock export."""
        return None, None

    def _chunk_output_for_display(self, content, chunk_prefix="PART"):
        """Mock display chunking."""
        return [content]


@pytest.fixture
def host() -> _FakeHost:
    """Create a fresh host instance."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _build_polish_prompts
# ---------------------------------------------------------------------------


class TestBuildPolishPrompts:
    """Tests for PolishStageMixin._build_polish_prompts."""

    def test_legacy_prompts(self, host: _FakeHost) -> None:
        """Test legacy prompt generation."""
        host._xml_enabled = False

        system, user_msg = host._build_polish_prompts(
            "input payload", "api_reference", "developers"
        )

        assert system is not None
        assert "senior technical editor" in system
        assert "input payload" in user_msg

    def test_xml_prompts(self, host: _FakeHost) -> None:
        """Test XML prompt generation."""
        host._xml_enabled = True

        system, user_msg = host._build_polish_prompts("input payload", "general", "beginners")

        assert system is None
        assert user_msg == "xml prompt"


# ---------------------------------------------------------------------------
# _execute_polish_llm
# ---------------------------------------------------------------------------


class TestExecutePolishLlm:
    """Tests for PolishStageMixin._execute_polish_llm."""

    @pytest.mark.asyncio
    async def test_legacy_path(self, host: _FakeHost) -> None:
        """Test legacy _call_llm path when no executor."""
        response, in_t, out_t = await host._execute_polish_llm(
            ModelTier.CAPABLE, "system", "user msg", 20000
        )
        assert response == "Polished document content."
        assert in_t == 100

    @pytest.mark.asyncio
    async def test_executor_path(self, host: _FakeHost) -> None:
        """Test executor path when api_key is set."""
        host._api_key = "test-key"

        response, in_t, out_t = await host._execute_polish_llm(
            ModelTier.PREMIUM, "system", "user msg", 20000
        )
        assert response == "Executor polished content."

    @pytest.mark.asyncio
    async def test_executor_fallback(self, host: _FakeHost) -> None:
        """Test fallback to _call_llm when executor fails."""
        host._api_key = "test-key"

        async def failing_executor(**kwargs):
            raise RuntimeError("executor down")

        host.run_step_with_executor = failing_executor

        response, _, _ = await host._execute_polish_llm(
            ModelTier.PREMIUM, "system", "user msg", 20000
        )
        assert response == "Polished document content."


# ---------------------------------------------------------------------------
# _build_polish_result
# ---------------------------------------------------------------------------


class TestBuildPolishResult:
    """Tests for PolishStageMixin._build_polish_result."""

    @patch(
        "attune.workflows.document_gen.polish_stage.format_doc_gen_report",
        return_value="formatted report",
    )
    def test_basic_result(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test basic result dict construction."""
        result = host._build_polish_result(
            "polished doc",
            "api_reference",
            "developers",
            ModelTier.CAPABLE,
            {},
            {},
        )

        assert result["document"] == "polished doc"
        assert result["doc_type"] == "api_reference"
        assert result["audience"] == "developers"
        assert result["model_tier_used"] == ModelTier.CAPABLE.value
        assert result["formatted_report"] == "formatted report"

    @patch(
        "attune.workflows.document_gen.polish_stage.format_doc_gen_report",
        return_value="report",
    )
    def test_xml_parsed_data_merged(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that XML parsed data is merged into result."""
        parsed_data = {
            "xml_parsed": True,
            "summary": "test summary",
            "findings": [{"id": 1}],
            "checklist": ["item"],
        }

        result = host._build_polish_result(
            "doc", "general", "devs", ModelTier.CHEAP, {}, parsed_data
        )

        assert result["xml_parsed"] is True
        assert result["summary"] == "test summary"

    @patch(
        "attune.workflows.document_gen.polish_stage.format_doc_gen_report",
        return_value="report",
    )
    def test_export_path_included(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
        tmp_path: Path,
    ) -> None:
        """Test that export path is included when export succeeds."""
        doc_path = tmp_path / "doc.md"
        doc_path.write_text("content", encoding="utf-8")

        host._export_document = lambda document, doc_type, report=None: (
            doc_path,
            None,
        )

        result = host._build_polish_result("doc", "general", "devs", ModelTier.CHEAP, {}, {})

        assert result["export_path"] == str(doc_path)


# ---------------------------------------------------------------------------
# _polish stage
# ---------------------------------------------------------------------------


class TestPolishStage:
    """Tests for PolishStageMixin._polish."""

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.document_gen.polish_stage.format_doc_gen_report",
        return_value="report",
    )
    async def test_small_doc_single_pass(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that small documents use single-pass polish."""
        input_data = {
            "draft_document": "Small document content",
            "doc_type": "general",
            "audience": "developers",
            "source_code": "def foo(): pass",
        }

        result, in_t, out_t = await host._polish(input_data, ModelTier.CAPABLE)

        # Should use single-pass (not chunked)
        assert "document" in result
        assert "API Ref" in result["document"]  # From _add_api_reference_sections

    @pytest.mark.asyncio
    async def test_large_doc_uses_chunked(self, host: _FakeHost) -> None:
        """Test that large documents use chunked polish."""
        # Create document > 10000 tokens (~40000 chars)
        large_doc = "x" * 50000

        input_data = {
            "draft_document": large_doc,
            "doc_type": "general",
            "audience": "developers",
        }

        result, _, _ = await host._polish(input_data, ModelTier.CAPABLE)

        assert result["document"] == "chunked polished"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.document_gen.polish_stage.format_doc_gen_report",
        return_value="report",
    )
    async def test_polish_no_source_code(
        self,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test polish without source code skips API reference."""
        input_data = {
            "draft_document": "Small doc",
            "doc_type": "general",
            "audience": "devs",
        }

        result, _, _ = await host._polish(input_data, ModelTier.CAPABLE)

        # No API reference added
        assert "API Ref" not in result["document"]
