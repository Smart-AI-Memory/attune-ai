"""Behavioral tests for AgentSDKResultAdapter.

Tests the adapter that converts Agent SDK output text into
WorkflowResult objects, covering conversion, stage mapping,
edge cases, cost reporting, summary extraction, and suggestion
extraction.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from attune.workflows.agent_sdk_adapter import AgentSDKResultAdapter
from attune.workflows.data_classes import (
    CostReport,
    NextAction,
    WorkflowResult,
    WorkflowStage,
)


def _now() -> datetime:
    """Return a timezone-aware UTC datetime for test fixtures."""
    return datetime.now(timezone.utc)


_SAMPLE_REVIEW = """\
## Summary
Code health score: 85/100. Generally solid codebase with minor issues.

## Security
- No eval/exec usage found
- Path validation in place

## Quality
- Good naming conventions
- Missing docstrings in 3 modules

## Performance
- No N+1 patterns detected

## Architecture
- Clean module boundaries

## Suggestions
- Consider adding input validation
- Run security audit quarterly
"""

_SUBAGENT_NAMES = [
    "security-reviewer",
    "quality-reviewer",
    "perf-reviewer",
    "architect-reviewer",
]


@pytest.mark.unit
class TestAgentSDKResultAdapterConversion:
    """Test from_agent_output produces a valid WorkflowResult."""

    def test_converts_agent_output_to_workflow_result(self) -> None:
        """Given sample review text, adapter returns a WorkflowResult."""
        started = _now()
        completed = _now()

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=started,
            completed_at=completed,
        )

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.final_output == _SAMPLE_REVIEW
        assert result.provider == "anthropic"
        assert result.error is None

    def test_metadata_includes_source_and_count(self) -> None:
        """Given subagent names, metadata has source and count."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.metadata["source"] == "agent_sdk"
        assert result.metadata["subagent_count"] == 4

    def test_custom_metadata_merged(self) -> None:
        """Given extra metadata, it is merged into result metadata."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            metadata={"path": "/src", "depth": "standard"},
        )

        assert result.metadata["path"] == "/src"
        assert result.metadata["depth"] == "standard"


@pytest.mark.unit
class TestAgentSDKResultAdapterStages:
    """Test subagent-to-stage mapping."""

    def test_maps_subagent_names_to_stages(self) -> None:
        """Given 4 subagent names, adapter creates 4 WorkflowStage objects."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert len(result.stages) == 4
        for stage in result.stages:
            assert isinstance(stage, WorkflowStage)

    def test_stage_names_match_subagent_names(self) -> None:
        """Given subagent names, stage names match them exactly."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        stage_names = [s.name for s in result.stages]
        assert stage_names == _SUBAGENT_NAMES

    def test_empty_subagents_produces_no_stages(self) -> None:
        """Given empty subagent list, stages list is empty."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=[],
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.stages == []


@pytest.mark.unit
class TestAgentSDKResultAdapterEdgeCases:
    """Test edge cases and malformed input."""

    def test_handles_empty_result_text(self) -> None:
        """Given empty string, adapter returns valid WorkflowResult."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text="",
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.final_output == ""

    def test_handles_malformed_output(self) -> None:
        """Given random text with no sections, adapter returns valid result."""
        malformed = "This is just random text with no markdown sections at all."

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=malformed,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.suggestions == []

    def test_handles_none_result_text(self) -> None:
        """Given None as result_text, adapter handles gracefully."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=None,  # type: ignore[arg-type]
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert isinstance(result, WorkflowResult)
        assert result.success is True


@pytest.mark.unit
class TestAgentSDKResultAdapterCostReport:
    """Test cost report generation."""

    def test_cost_report_zero_for_subscription(self) -> None:
        """Given subscription execution, total_cost is 0.0."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert isinstance(result.cost_report, CostReport)
        assert result.cost_report.total_cost == 0.0
        assert result.cost_report.baseline_cost == 0.0
        assert result.cost_report.savings == 0.0

    def test_cost_report_by_stage_has_all_subagents(self) -> None:
        """Given subagent names, by_stage dict has an entry per agent."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert len(result.cost_report.by_stage) == 4
        for name in _SUBAGENT_NAMES:
            assert name in result.cost_report.by_stage
            assert result.cost_report.by_stage[name] == 0.0


@pytest.mark.unit
class TestAgentSDKResultAdapterSummaryExtraction:
    """Test summary extraction from agent output."""

    def test_extracts_summary_from_section(self) -> None:
        """Given text with ## Summary section, summary is extracted."""
        text = "## Summary\n" "This is the summary.\n\n" "## Security\n" "No issues found.\n"

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.summary == "This is the summary."

    def test_summary_falls_back_to_first_paragraph(self) -> None:
        """Given text without ## Summary, falls back to first paragraph."""
        text = "First paragraph of the review.\n\nSecond paragraph."

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.summary == "First paragraph of the review."

    def test_empty_text_returns_empty_summary(self) -> None:
        """Given empty text, summary is empty string."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text="",
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.summary == ""


@pytest.mark.unit
class TestAgentSDKResultAdapterSuggestionExtraction:
    """Test suggestion extraction as NextAction items."""

    def test_extracts_suggestions_from_section(self) -> None:
        """Given text with ## Suggestions section, NextAction list is populated."""
        text = (
            "## Summary\n"
            "OK.\n\n"
            "## Suggestions\n"
            "- Consider adding input validation\n"
            "- Run security audit\n"
        )

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert len(result.suggestions) == 2
        for s in result.suggestions:
            assert isinstance(s, NextAction)
            assert s.workflow_name == "agent-followup"

    def test_suggestion_descriptions_match_bullets(self) -> None:
        """Given bullet items, descriptions capture the text."""
        text = (
            "## Suggestions\n"
            "- Consider adding input validation\n"
            "- Run security audit quarterly\n"
        )

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        descriptions = [s.description for s in result.suggestions]
        assert "Consider adding input validation" in descriptions
        assert "Run security audit quarterly" in descriptions

    def test_no_suggestions_section_returns_empty_list(self) -> None:
        """Given text without suggestion-like content, list is empty."""
        text = "## Summary\nAll good.\n\n## Security\nNo issues.\n"

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        assert result.suggestions == []

    def test_fallback_extracts_suggestion_phrased_bullets(self) -> None:
        """Given text with 'consider' bullets outside a section, fallback fires."""
        text = "## Security\n" "- Consider using parameterized queries\n" "- No eval usage found\n"

        result = AgentSDKResultAdapter.from_agent_output(
            result_text=text,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )

        # Fallback should pick up the "Consider" bullet
        assert len(result.suggestions) >= 1
        assert any("parameterized queries" in s.description for s in result.suggestions)
