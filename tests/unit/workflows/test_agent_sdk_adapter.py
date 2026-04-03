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

from attune.workflows.agent_sdk_adapter import (
    AgentRunResult,
    AgentSDKResultAdapter,
    get_max_budget_usd,
    get_subagent_model,
)
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
        # final_output is formatted from parsed findings
        assert "No eval/exec usage found" in result.final_output
        assert "Good naming conventions" in result.final_output
        assert "Clean module boundaries" in result.final_output
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


@pytest.mark.unit
class TestAgentRunResultDataclass:
    """Test the AgentRunResult dataclass."""

    def test_defaults(self) -> None:
        """Given only result_text, all other fields have sane defaults."""
        r = AgentRunResult(result_text="hello")
        assert r.result_text == "hello"
        assert r.total_cost_usd is None
        assert r.usage is None
        assert r.duration_ms == 0
        assert r.num_turns == 0
        assert r.session_id is None
        assert r.is_error is False


@pytest.mark.unit
class TestAgentSDKResultAdapterCostExtraction:
    """Test cost/usage extraction from AgentRunResult."""

    def test_api_key_cost_populates_cost_report(self) -> None:
        """Given total_cost_usd, cost_report reflects actual cost."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            total_cost_usd=0.05,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert result.cost_report.total_cost == 0.05
        assert result.cost_report.baseline_cost == 0.05

    def test_subscription_none_cost_defaults_to_zero(self) -> None:
        """Given total_cost_usd=None (subscription), cost is 0.0."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            total_cost_usd=None,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert result.cost_report.total_cost == 0.0

    def test_backward_compat_without_agent_run_result(self) -> None:
        """Given no agent_run_result, existing zero-cost behavior is preserved."""
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
        )
        assert result.cost_report.total_cost == 0.0
        assert "num_turns" not in result.metadata

    def test_usage_tokens_populate_stages(self) -> None:
        """Given usage dict with tokens, stages get token counts."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            usage={"input_tokens": 4000, "output_tokens": 2000},
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        # 4 subagents, tokens split evenly
        for stage in result.stages:
            assert stage.input_tokens == 1000
            assert stage.output_tokens == 500

    def test_sdk_metadata_in_result(self) -> None:
        """Given agent_run_result, metadata includes SDK fields."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            num_turns=15,
            session_id="sess-abc123",
            duration_api_ms=5000,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert result.metadata["num_turns"] == 15
        assert result.metadata["session_id"] == "sess-abc123"
        assert result.metadata["duration_api_ms"] == 5000


@pytest.mark.unit
class TestGetMaxBudgetUsd:
    """Test budget helper for workflow depth caps."""

    def test_quick_depth_returns_half_dollar(self) -> None:
        """Given 'quick' depth, returns 0.50."""
        assert get_max_budget_usd("quick") == 0.50

    def test_standard_depth_returns_two_dollars(self) -> None:
        """Given 'standard' depth, returns 2.00."""
        assert get_max_budget_usd("standard") == 2.00

    def test_deep_depth_returns_five_dollars(self) -> None:
        """Given 'deep' depth, returns 5.00."""
        assert get_max_budget_usd("deep") == 5.00

    def test_unknown_depth_falls_back_to_standard(self) -> None:
        """Given unknown depth, returns 2.00 (standard default)."""
        assert get_max_budget_usd("unknown") == 2.00

    def test_default_depth_is_standard(self) -> None:
        """Given no argument, defaults to 'standard' (2.00)."""
        assert get_max_budget_usd() == 2.00

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given ATTUNE_MAX_BUDGET_USD env var, overrides depth default."""
        monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "10.0")
        assert get_max_budget_usd("quick") == 10.0

    def test_env_var_zero_disables_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given ATTUNE_MAX_BUDGET_USD=0, returns None (no cap)."""
        monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "0")
        assert get_max_budget_usd("deep") is None


@pytest.mark.unit
class TestGetSubagentModel:
    """Test per-agent model selection helper."""

    def test_security_agent_gets_opus(self) -> None:
        """Given 'security-reviewer', returns 'opus'."""
        assert get_subagent_model("security-reviewer") == "opus"

    def test_vuln_agent_gets_opus(self) -> None:
        """Given 'vuln-scanner', returns 'opus'."""
        assert get_subagent_model("vuln-scanner") == "opus"

    def test_architect_agent_gets_opus(self) -> None:
        """Given 'architect-reviewer', returns 'opus'."""
        assert get_subagent_model("architect-reviewer") == "opus"

    def test_quality_agent_gets_sonnet(self) -> None:
        """Given 'quality-reviewer', returns 'sonnet'."""
        assert get_subagent_model("quality-reviewer") == "sonnet"

    def test_complexity_agent_gets_haiku(self) -> None:
        """Given 'complexity-analyzer', returns 'haiku'."""
        assert get_subagent_model("complexity-analyzer") == "haiku"

    def test_lint_agent_gets_haiku(self) -> None:
        """Given 'lint-checker', returns 'haiku'."""
        assert get_subagent_model("lint-checker") == "haiku"

    def test_unknown_agent_returns_none(self) -> None:
        """Given unmatched name, returns None (inherit parent)."""
        assert get_subagent_model("unknown-agent") is None

    def test_perf_reviewer_returns_none(self) -> None:
        """Given 'perf-reviewer' (no keyword match), returns None."""
        assert get_subagent_model("perf-reviewer") is None

    def test_env_var_keyword_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Given ATTUNE_AGENT_MODEL_SECURITY=sonnet, overrides default."""
        monkeypatch.setenv("ATTUNE_AGENT_MODEL_SECURITY", "sonnet")
        assert get_subagent_model("security-reviewer") == "sonnet"

    def test_env_var_inherit_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Given ATTUNE_AGENT_MODEL_LINT=inherit, returns None."""
        monkeypatch.setenv("ATTUNE_AGENT_MODEL_LINT", "inherit")
        assert get_subagent_model("lint-checker") is None

    def test_global_default_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Given ATTUNE_AGENT_MODEL_DEFAULT=opus, unmatched agents get opus."""
        monkeypatch.setenv("ATTUNE_AGENT_MODEL_DEFAULT", "opus")
        assert get_subagent_model("perf-reviewer") == "opus"

    def test_global_default_inherit_returns_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Given ATTUNE_AGENT_MODEL_DEFAULT=inherit, returns None."""
        monkeypatch.setenv("ATTUNE_AGENT_MODEL_DEFAULT", "inherit")
        assert get_subagent_model("perf-reviewer") is None

    def test_case_insensitive_matching(self) -> None:
        """Given mixed-case name, keyword matching is case-insensitive."""
        assert get_subagent_model("Security-Reviewer") == "opus"


@pytest.mark.unit
class TestAgentSDKResultAdapterStructuredOutput:
    """Test structured output dual-path in from_agent_output."""

    _STRUCTURED_DATA: dict = {
        "summary": {"score": 90, "text": "Code is solid."},
        "findings": {
            "security": [
                {"description": "No eval usage", "severity": "low"},
            ],
        },
        "suggestions": [
            {"description": "Add input validation", "priority": "high"},
            {"description": "Run audit quarterly", "priority": "medium"},
        ],
    }

    def test_structured_output_populates_summary(self) -> None:
        """Given structured_output dict, summary comes from JSON."""
        run = AgentRunResult(
            result_text="fallback text",
            structured_output=self._STRUCTURED_DATA,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text="fallback text",
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert result.summary == "Code is solid."

    def test_structured_output_populates_findings(self) -> None:
        """Given structured_output dict, findings come from JSON."""
        run = AgentRunResult(
            result_text="fallback text",
            structured_output=self._STRUCTURED_DATA,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text="fallback text",
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert "security" in result.metadata["findings"]

    def test_structured_output_populates_suggestions(self) -> None:
        """Given structured_output dict, suggestions have high confidence."""
        run = AgentRunResult(
            result_text="fallback text",
            structured_output=self._STRUCTURED_DATA,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text="fallback text",
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert len(result.suggestions) == 2
        assert all(s.confidence == 0.9 for s in result.suggestions)
        assert result.suggestions[0].priority == "high"

    def test_none_structured_output_falls_back_to_text(self) -> None:
        """Given structured_output=None, text parsing fires."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            structured_output=None,
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        # Text parsing should find the ## Summary section
        assert "85/100" in result.summary

    def test_non_dict_structured_output_falls_back_to_text(self) -> None:
        """Given structured_output as string, text parsing fires."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            structured_output="not a dict",
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        assert "85/100" in result.summary

    def test_empty_structured_output_falls_back_to_text(self) -> None:
        """Given empty dict structured_output, text parsing fires."""
        run = AgentRunResult(
            result_text=_SAMPLE_REVIEW,
            structured_output={},
        )
        result = AgentSDKResultAdapter.from_agent_output(
            result_text=_SAMPLE_REVIEW,
            subagent_names=_SUBAGENT_NAMES,
            started_at=_now(),
            completed_at=_now(),
            agent_run_result=run,
        )
        # Empty dict is falsy, so falls back to text parsing
        assert "85/100" in result.summary
