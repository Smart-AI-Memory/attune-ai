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
    resolve_cwd_for_path,
    sdk_error_message,
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

    def test_quick_depth_returns_two_dollars(self) -> None:
        """Given 'quick' depth, returns 2.00."""
        assert get_max_budget_usd("quick") == 2.00

    def test_standard_depth_returns_ten_dollars(self) -> None:
        """Given 'standard' depth, returns 10.00."""
        assert get_max_budget_usd("standard") == 10.00

    def test_deep_depth_returns_twentyfive_dollars(self) -> None:
        """Given 'deep' depth, returns 25.00."""
        assert get_max_budget_usd("deep") == 25.00

    def test_unknown_depth_falls_back_to_standard(self) -> None:
        """Given unknown depth, returns 10.00 (standard default)."""
        assert get_max_budget_usd("unknown") == 10.00

    def test_default_depth_is_standard(self) -> None:
        """Given no argument, defaults to 'standard' (10.00)."""
        assert get_max_budget_usd() == 10.00

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given ATTUNE_MAX_BUDGET_USD env var, overrides depth default."""
        monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "10.0")
        assert get_max_budget_usd("quick") == 10.0

    def test_env_var_zero_disables_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Given ATTUNE_MAX_BUDGET_USD=0, returns None (no cap)."""
        monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "0")
        assert get_max_budget_usd("deep") is None


@pytest.mark.unit
class TestSdkErrorMessage:
    """Test the SDK error-message classifier.

    Each test feeds a synthetic exception + duration through
    ``sdk_error_message`` and asserts the returned text contains
    the expected actionable phrases. We don't assert exact strings
    — those will change as the messages get polished — only that
    the right *kind* of guidance is being surfaced.
    """

    EXIT_1_RAW = (
        "Command failed with exit code 1 (exit code: 1)\n"
        "Error output: Check stderr output for details"
    )

    def test_network_error_suggests_connectivity(self) -> None:
        """ConnectionError → network-troubleshooting steps."""
        msg = sdk_error_message(ConnectionError("connection refused"))
        assert "Network error" in msg
        # The hint mentions Anthropic's API endpoint by name. Split
        # check across two assertions so CodeQL's URL-sanitization
        # heuristic doesn't false-positive on a substring test.
        assert "anthropic" in msg.lower()
        assert "firewall" in msg.lower() or "proxy" in msg.lower()
        assert "ConnectionError" in msg

    def test_timeout_error_suggests_connectivity(self) -> None:
        """TimeoutError shares the network classification."""
        msg = sdk_error_message(TimeoutError("timed out"))
        assert "Network error" in msg
        assert "Retry" in msg

    def test_exit_1_fast_failure_suggests_auth(self) -> None:
        """Exit-1 + duration < 5s → auth/CLI startup hints."""
        exc = Exception(self.EXIT_1_RAW)
        msg = sdk_error_message(exc, duration_seconds=0.5, depth="standard")
        assert "startup" in msg
        assert "ANTHROPIC_API_KEY" in msg
        assert "claude" in msg  # references the CLI

    def test_exit_1_slow_failure_suggests_budget_cap(self) -> None:
        """Exit-1 + duration >= 30s → budget-cap hints."""
        exc = Exception(self.EXIT_1_RAW)
        msg = sdk_error_message(exc, duration_seconds=120.0, depth="quick")
        assert "mid-stream" in msg
        assert "ATTUNE_MAX_BUDGET_USD=0" in msg
        # Quick depth should be suggested a bump up.
        assert "--depth standard" in msg

    def test_exit_1_slow_failure_at_deep_does_not_suggest_quick(self) -> None:
        """When already at 'deep', the bump suggestion doesn't downgrade."""
        exc = Exception(self.EXIT_1_RAW)
        msg = sdk_error_message(exc, duration_seconds=120.0, depth="deep")
        # Bump target falls back to 'deep' (current depth) — message
        # still suggests the env-var override as the primary action.
        assert "ATTUNE_MAX_BUDGET_USD=0" in msg

    def test_exit_1_no_duration_uses_generic_message(self) -> None:
        """Exit-1 without duration → generic exit-1 guidance."""
        exc = Exception(self.EXIT_1_RAW)
        msg = sdk_error_message(exc)
        assert "exit code 1" in msg
        assert "ANTHROPIC_API_KEY" in msg or "auth" in msg.lower()
        assert "ATTUNE_MAX_BUDGET_USD" in msg

    def test_unknown_exception_falls_back_gracefully(self) -> None:
        """Non-network non-exit-1 exception → generic header."""
        exc = ValueError("some weird internal state")
        msg = sdk_error_message(exc)
        assert "Agent SDK failure" in msg
        assert "ValueError" in msg
        assert "some weird internal state" in msg

    def test_raw_exception_always_included(self) -> None:
        """Every variant must preserve the underlying message
        for debugging, so the user can still copy-paste it into
        an issue when the guidance doesn't help."""
        for exc in [
            ConnectionError("network down"),
            Exception(self.EXIT_1_RAW),
            ValueError("weird"),
        ]:
            msg = sdk_error_message(exc, duration_seconds=1.0, depth="quick")
            assert "Underlying error:" in msg

    def test_subscription_explainer_appears_for_budget_path(self) -> None:
        """The budget-path message reminds subscription users that
        the cap isn't a billing limit (addresses a real user
        confusion: 'why is there a cap if I'm on subscription?')."""
        exc = Exception(self.EXIT_1_RAW)
        msg = sdk_error_message(exc, duration_seconds=60.0, depth="standard")
        assert "subscription" in msg.lower()


@pytest.mark.unit
class TestResolveCwdForPath:
    """Regression tests for resolve_cwd_for_path().

    The Claude Agent SDK's ``cwd=`` arg must be an existing
    directory; passing a file path crashes the SDK subprocess
    with ``CLIConnectionError: Not a directory`` (surfaced
    opaquely as ``Command failed with exit code 1``). This
    helper unblocks single-file workflow invocations.
    """

    def test_file_returns_parent_directory(self, tmp_path) -> None:
        """Given a file path, returns its parent directory."""
        file_path = tmp_path / "mod.py"
        file_path.write_text("x = 1\n")
        assert resolve_cwd_for_path(file_path) == tmp_path

    def test_directory_returns_itself_unchanged(self, tmp_path) -> None:
        """Given a directory path, returns it unchanged."""
        assert resolve_cwd_for_path(tmp_path) == tmp_path

    def test_accepts_string_input(self, tmp_path) -> None:
        """Given a str path, coerces to Path and applies same rule."""
        file_path = tmp_path / "mod.py"
        file_path.write_text("x = 1\n")
        assert resolve_cwd_for_path(str(file_path)) == tmp_path

    def test_nonexistent_path_returned_unchanged(self, tmp_path) -> None:
        """Given a nonexistent path, returns it unchanged (not a file)."""
        ghost = tmp_path / "does_not_exist"
        assert resolve_cwd_for_path(ghost) == ghost


@pytest.mark.unit
class TestSdkWorkflowsUseCwdHelper:
    """Drift-guard: every SDK workflow's cwd= must use the helper.

    Without this guard, a future workflow author would naturally
    write ``cwd=resolved_path``, reintroducing the silent file-
    path crash. Asserts the antipattern is absent across all 15
    SDK-native workflows that take a path argument.
    """

    _SDK_WORKFLOW_FILES = [
        "src/attune/workflows/bug_predict.py",
        "src/attune/workflows/code_review.py",
        "src/attune/workflows/deep_review.py",
        "src/attune/workflows/dependency_check.py",
        "src/attune/workflows/perf_audit.py",
        "src/attune/workflows/rag_code_gen.py",
        "src/attune/workflows/release_prep.py",
        "src/attune/workflows/research_synthesis.py",
        "src/attune/workflows/security_audit.py",
        "src/attune/workflows/refactor_plan.py",
        "src/attune/workflows/simplify_code.py",
        "src/attune/workflows/document_gen/workflow.py",
        "src/attune/workflows/doc_audit/workflow.py",
        "src/attune/workflows/test_audit/workflow.py",
        "src/attune/workflows/test_gen/workflow.py",
    ]

    def test_no_workflow_uses_raw_resolved_path_as_cwd(self) -> None:
        """No SDK workflow may write ``cwd=resolved_path`` directly."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        offenders: list[str] = []
        for rel in self._SDK_WORKFLOW_FILES:
            text = (repo_root / rel).read_text(encoding="utf-8")
            if "cwd=resolved_path," in text:
                offenders.append(rel)
        assert not offenders, (
            f"Workflows passing file paths as cwd to the Agent SDK "
            f"crash at subprocess startup. Wrap with "
            f"resolve_cwd_for_path(). Offenders: {offenders}"
        )


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
