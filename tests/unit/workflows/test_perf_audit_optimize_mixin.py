"""Unit tests for attune.workflows.perf_audit_optimize_mixin module.

Tests cover:
- PerfAuditOptimizeMixin._optimize: prompt building, LLM call, result assembly
- _build_optimize_prompt: XML vs legacy prompt construction
- _execute_optimize_llm: executor vs legacy LLM fallback

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.perf_audit_optimize_mixin import (
    PerfAuditOptimizeMixin,
    _build_optimize_prompt,
    _execute_optimize_llm,
)


class _FakeHost(PerfAuditOptimizeMixin):
    """Minimal host providing attributes expected by the mixin."""

    def __init__(self) -> None:
        self._auth_mode_used: str | None = "subscription"
        self._executor = None
        self._api_key: str | None = None
        self._is_xml_enabled_val: bool = False

    def _is_xml_enabled(self) -> bool:
        """Return whether XML prompts are enabled."""
        return self._is_xml_enabled_val

    def _render_xml_prompt(self, **kwargs) -> str:
        """Return a mock XML prompt."""
        return "xml prompt content"

    def _parse_xml_response(self, response: str) -> dict:
        """Parse XML response (mock)."""
        return {}

    async def _call_llm(self, tier, system, user_msg, max_tokens=3000) -> tuple[str, int, int]:
        """Mock LLM call."""
        return "optimization plan", 100, 200

    async def run_step_with_executor(self, step, prompt, system=None):
        """Mock executor step."""
        return "executor response", 50, 100, 0.01


# ---------------------------------------------------------------------------
# _build_optimize_prompt
# ---------------------------------------------------------------------------


class TestBuildOptimizePrompt:
    """Tests for _build_optimize_prompt helper."""

    def test_legacy_prompt_no_xml(self) -> None:
        """Test that legacy prompt is built when XML is disabled."""
        host = _FakeHost()
        host._is_xml_enabled_val = False

        system, user_msg = _build_optimize_prompt(
            host,
            "input payload text",
            {"perf_score": 85, "perf_level": "good"},
            [],
        )

        assert system is not None
        assert "performance engineer" in system
        assert "input payload text" in user_msg

    def test_xml_prompt_enabled(self) -> None:
        """Test that XML prompt is built when enabled."""
        host = _FakeHost()
        host._is_xml_enabled_val = True

        system, user_msg = _build_optimize_prompt(
            host,
            "input payload",
            {"perf_score": 50},
            [{"file": "a.py"}],
        )

        assert system is None  # XML mode uses no system prompt
        assert user_msg == "xml prompt content"


# ---------------------------------------------------------------------------
# _execute_optimize_llm
# ---------------------------------------------------------------------------


class TestExecuteOptimizeLlm:
    """Tests for _execute_optimize_llm helper."""

    @pytest.mark.asyncio
    async def test_legacy_path_when_no_executor(self) -> None:
        """Test that legacy _call_llm is used when no executor."""
        host = _FakeHost()
        host._executor = None
        host._api_key = None

        response, in_t, out_t = await _execute_optimize_llm(
            host, ModelTier.CHEAP, "system", "user msg"
        )

        assert response == "optimization plan"
        assert in_t == 100
        assert out_t == 200

    @pytest.mark.asyncio
    async def test_executor_path_when_api_key_set(self) -> None:
        """Test that executor is tried when api_key is set."""
        host = _FakeHost()
        host._api_key = "test-key"

        response, in_t, out_t = await _execute_optimize_llm(
            host, ModelTier.PREMIUM, "system", "user msg"
        )

        assert response == "executor response"
        assert in_t == 50

    @pytest.mark.asyncio
    async def test_executor_fallback_on_error(self) -> None:
        """Test fallback to _call_llm when executor raises."""
        host = _FakeHost()
        host._api_key = "test-key"

        async def failing_executor(**kwargs):
            raise RuntimeError("executor failed")

        host.run_step_with_executor = failing_executor

        response, in_t, out_t = await _execute_optimize_llm(
            host, ModelTier.PREMIUM, "system", "user msg"
        )

        # Should fall back to _call_llm
        assert response == "optimization plan"


# ---------------------------------------------------------------------------
# _optimize stage
# ---------------------------------------------------------------------------


class TestOptimizeStage:
    """Tests for PerfAuditOptimizeMixin._optimize."""

    @pytest.fixture
    def host(self) -> _FakeHost:
        """Create a host instance."""
        return _FakeHost()

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.format_perf_audit_report",
        return_value="formatted report",
    )
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.create_perf_audit_workflow_report",
        return_value=MagicMock(),
    )
    async def test_optimize_basic(
        self,
        mock_wf_report: MagicMock,
        mock_format: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test basic optimize stage execution."""
        input_data = {
            "hotspot_result": {
                "hotspots": [
                    {"file": "a.py", "complexity_score": 20, "concerns": ["n_plus_one"]},
                ],
                "perf_score": 60,
                "perf_level": "warning",
            },
            "findings": [
                {"type": "n_plus_one"},
                {"type": "n_plus_one"},
            ],
            "target": "src/",
        }

        result, in_t, out_t = await host._optimize(input_data, ModelTier.PREMIUM)

        assert "optimization_plan" in result
        assert result["perf_score"] == 60
        assert result["perf_level"] == "warning"
        assert result["auth_mode_used"] == "subscription"
        assert result["formatted_report"] == "formatted report"

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.format_perf_audit_report",
        return_value="report",
    )
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.create_perf_audit_workflow_report",
        return_value=MagicMock(),
    )
    async def test_optimize_empty_hotspots(
        self,
        mock_wf: MagicMock,
        mock_fmt: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test optimize with no hotspots."""
        input_data = {
            "hotspot_result": {"hotspots": [], "perf_score": 100, "perf_level": "good"},
            "findings": [],
        }

        result, _, _ = await host._optimize(input_data, ModelTier.CHEAP)

        assert result["recommendation_count"] == 0
        assert result["top_issues"] == []

    @pytest.mark.asyncio
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.format_perf_audit_report",
        return_value="report",
    )
    @patch(
        "attune.workflows.perf_audit_optimize_mixin.create_perf_audit_workflow_report",
        return_value=MagicMock(),
    )
    async def test_optimize_xml_parsed_data(
        self,
        mock_wf: MagicMock,
        mock_fmt: MagicMock,
        host: _FakeHost,
    ) -> None:
        """Test that parsed XML data is merged into result."""
        host._parse_xml_response = lambda r: {
            "xml_parsed": True,
            "summary": "test summary",
            "findings": [{"id": 1}],
            "checklist": ["item1"],
        }

        input_data = {
            "hotspot_result": {"hotspots": [], "perf_score": 90, "perf_level": "good"},
            "findings": [],
        }

        result, _, _ = await host._optimize(input_data, ModelTier.CHEAP)

        assert result["xml_parsed"] is True
        assert result["summary"] == "test summary"
        assert result["findings"] == [{"id": 1}]
