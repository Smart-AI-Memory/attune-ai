"""Tests for project-aware guidance suggestion engine.

Tests the NextAction dataclass, suggestion generation,
transition registry, formatting utilities, project index signals,
workflow history patterns, and suggestion persistence.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

# ============================================================================
# FIXTURES
# ============================================================================
import pytest

from attune.workflows.data_classes import (
    CostReport,
    NextAction,
    WorkflowResult,
)
from attune.workflows.suggestions import (
    MAX_SUGGESTIONS,
    _extract_output_text,
    _filter_recently_shown,
    _suggestions_from_history,
    _suggestions_from_project_index,
    format_suggestions_markdown,
    generate_suggestions,
    record_suggestions_shown,
    suggestions_to_options,
)


@pytest.fixture(autouse=True)
def _isolate_suggestions(tmp_path, monkeypatch):
    """Isolate all suggestion tests from real filesystem.

    Changes to tmp_path so project index reads and suggestion
    state persistence don't affect the real working directory.
    """
    monkeypatch.chdir(tmp_path)


def _make_result(
    success: bool = True,
    final_output: str = "",
    error: str | None = None,
    error_type: str | None = None,
    transient: bool = False,
) -> WorkflowResult:
    """Create a minimal WorkflowResult for testing."""
    now = datetime.now()
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output,
        cost_report=CostReport(
            total_cost=0.01,
            baseline_cost=0.05,
            savings=0.04,
            savings_percent=80.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=100,
        error=error,
        error_type=error_type,
        transient=transient,
    )


# ============================================================================
# NEXT ACTION DATACLASS
# ============================================================================


class TestNextAction:
    """Tests for NextAction dataclass."""

    def test_creation_with_defaults(self):
        """Test NextAction uses correct defaults."""
        action = NextAction(
            workflow_name="test-gen",
            description="Generate tests",
            reasoning="Improve coverage",
        )
        assert action.priority == "medium"
        assert action.confidence == 0.8

    def test_creation_with_custom_values(self):
        """Test NextAction accepts custom values."""
        action = NextAction(
            workflow_name="security-audit",
            description="Run security audit",
            reasoning="Found vulnerabilities",
            priority="high",
            confidence=0.95,
        )
        assert action.workflow_name == "security-audit"
        assert action.priority == "high"
        assert action.confidence == 0.95


# ============================================================================
# WORKFLOW RESULT SUGGESTIONS FIELD
# ============================================================================


class TestWorkflowResultSuggestions:
    """Tests for suggestions field on WorkflowResult."""

    def test_default_empty_suggestions(self):
        """Test WorkflowResult defaults to empty suggestions list."""
        result = _make_result()
        assert result.suggestions == []

    def test_suggestions_field_populated(self):
        """Test suggestions can be populated on WorkflowResult."""
        result = _make_result()
        result.suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Low coverage",
            ),
        ]
        assert len(result.suggestions) == 1
        assert result.suggestions[0].workflow_name == "test-gen"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


class TestHelpers:
    """Tests for helper functions."""

    def test_extract_output_text_string(self):
        """Test extracting text from string output."""
        assert _extract_output_text("Found SECURITY issues") == "found security issues"

    def test_extract_output_text_dict(self):
        """Test extracting text from dict output."""
        text = _extract_output_text({"findings": "security issue"})
        assert "security" in text

    def test_extract_output_text_none(self):
        """Test extracting text from None output."""
        assert _extract_output_text(None) == ""


# ============================================================================
# TRANSITION REGISTRY
# ============================================================================


class TestCodeReviewTransitions:
    """Tests for code-review workflow transitions."""

    def test_security_findings_suggest_security_audit(self):
        """Test that security keywords trigger security-audit suggestion."""
        result = _make_result(final_output="Found path traversal vulnerability in config.py")
        suggestions = generate_suggestions("code-review", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "security-audit" in workflow_names

    def test_perf_findings_suggest_perf_audit(self):
        """Test that performance keywords trigger perf-audit suggestion."""
        result = _make_result(final_output="Slow database query with N+1 performance bottleneck")
        suggestions = generate_suggestions("code-review", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "perf-audit" in workflow_names

    def test_successful_review_suggests_test_gen(self):
        """Test that successful review suggests test generation."""
        result = _make_result(final_output="Code review completed with findings")
        suggestions = generate_suggestions("code-review", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "test-gen" in workflow_names

    def test_security_suggestion_has_high_priority(self):
        """Test security suggestions get high priority."""
        result = _make_result(final_output="Multiple XSS injection vulnerabilities found")
        suggestions = generate_suggestions("code-review", result)
        security = next(s for s in suggestions if s.workflow_name == "security-audit")
        assert security.priority == "high"


class TestSecurityAuditTransitions:
    """Tests for security-audit workflow transitions."""

    def test_high_severity_suggests_dependency_check(self):
        """Test high severity findings suggest dependency check."""
        result = _make_result(final_output="Critical vulnerability: SQL injection in auth module")
        suggestions = generate_suggestions("security-audit", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "dependency-check" in workflow_names

    def test_successful_audit_suggests_release_prep(self):
        """Test successful audit suggests release prep."""
        result = _make_result(final_output="Audit complete: 2 low issues")
        suggestions = generate_suggestions("security-audit", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "release-prep" in workflow_names


class TestBugPredictTransitions:
    """Tests for bug-predict workflow transitions."""

    def test_high_risk_suggests_test_gen(self):
        """Test high risk findings suggest test generation."""
        result = _make_result(final_output="High risk: likely bug in auth module")
        suggestions = generate_suggestions("bug-predict", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "test-gen" in workflow_names

    def test_complexity_suggests_refactor(self):
        """Test complexity findings suggest refactor plan."""
        result = _make_result(
            final_output="Deeply nested complex module with high complexity score",
        )
        suggestions = generate_suggestions("bug-predict", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "refactor-plan" in workflow_names


class TestRefactorPlanTransitions:
    """Tests for refactor-plan workflow transitions."""

    def test_suggests_test_gen_first(self):
        """Test refactor plan suggests test-first approach."""
        result = _make_result(final_output="Refactor plan generated")
        suggestions = generate_suggestions("refactor-plan", result)
        assert len(suggestions) > 0
        assert suggestions[0].workflow_name == "test-gen"
        assert suggestions[0].priority == "high"


# ============================================================================
# SUGGESTION ENGINE
# ============================================================================


class TestGenerateSuggestions:
    """Tests for the main generate_suggestions function."""

    def test_max_suggestions_limit(self):
        """Test that suggestions are limited to MAX_SUGGESTIONS."""
        result = _make_result(
            final_output=(
                "security vulnerability, performance bottleneck, "
                "XSS injection, path traversal, slow query"
            ),
        )
        suggestions = generate_suggestions("code-review", result)
        assert len(suggestions) <= MAX_SUGGESTIONS

    def test_sorted_by_priority_then_confidence(self):
        """Test suggestions are sorted by priority then confidence."""
        result = _make_result(final_output="security vulnerability and performance slow")
        suggestions = generate_suggestions("code-review", result)
        if len(suggestions) >= 2:
            priority_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(suggestions) - 1):
                current_p = priority_order.get(suggestions[i].priority, 1)
                next_p = priority_order.get(suggestions[i + 1].priority, 1)
                if current_p == next_p:
                    assert suggestions[i].confidence >= suggestions[i + 1].confidence

    def test_unknown_workflow_returns_empty(self):
        """Test unregistered workflow returns empty suggestions."""
        result = _make_result(final_output="some output")
        suggestions = generate_suggestions("unknown-workflow", result)
        assert suggestions == []

    def test_failed_workflow_suggests_retry(self):
        """Test failed transient workflow suggests retry."""
        result = _make_result(
            success=False,
            error="API timeout",
            error_type="timeout",
            transient=True,
        )
        suggestions = generate_suggestions("code-review", result)
        assert len(suggestions) > 0
        assert suggestions[0].workflow_name == "code-review"
        assert "retry" in suggestions[0].description.lower()

    def test_config_failure_suggests_dependency_check(self):
        """Test config error suggests dependency check."""
        result = _make_result(
            success=False,
            error="Configuration error",
            error_type="config",
            transient=False,
        )
        suggestions = generate_suggestions("code-review", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert "dependency-check" in workflow_names

    def test_deduplicates_by_workflow_name(self):
        """Test that duplicate workflow targets are deduplicated."""
        result = _make_result(final_output="security vulnerability XSS injection path traversal")
        suggestions = generate_suggestions("code-review", result)
        workflow_names = [s.workflow_name for s in suggestions]
        assert len(workflow_names) == len(set(workflow_names))


# ============================================================================
# FORMATTING
# ============================================================================


class TestFormatSuggestionsMarkdown:
    """Tests for markdown formatting of suggestions."""

    def test_empty_suggestions_returns_empty(self):
        """Test empty list produces empty string."""
        assert format_suggestions_markdown([]) == ""

    def test_includes_header(self):
        """Test output includes What's Next header."""
        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Low coverage",
            ),
        ]
        output = format_suggestions_markdown(suggestions)
        assert "## What's Next" in output

    def test_includes_workflow_command(self):
        """Test output includes slash command format."""
        suggestions = [
            NextAction(
                workflow_name="security-audit",
                description="Run audit",
                reasoning="Found issues",
            ),
        ]
        output = format_suggestions_markdown(suggestions)
        assert "`/security-audit`" in output

    def test_includes_reasoning(self):
        """Test output includes reasoning in italics."""
        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage is below 80%",
            ),
        ]
        output = format_suggestions_markdown(suggestions)
        assert "*Coverage is below 80%*" in output


class TestSuggestionsToOptions:
    """Tests for AskUserQuestion option conversion."""

    def test_converts_to_option_format(self):
        """Test conversion to option dicts."""
        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests for uncovered modules",
                reasoning="Low coverage",
            ),
        ]
        options = suggestions_to_options(suggestions)
        assert len(options) == 1
        assert options[0]["label"] == "/test-gen"
        assert options[0]["description"] == "Generate tests for uncovered modules"

    def test_empty_suggestions_returns_empty(self):
        """Test empty input returns empty list."""
        assert suggestions_to_options([]) == []


# ============================================================================
# PROJECT INDEX SIGNALS
# ============================================================================


class TestProjectIndexSignals:
    """Tests for project index-based suggestions."""

    def test_low_coverage_suggests_test_gen(self, tmp_path, monkeypatch):
        """Test low coverage triggers test-gen suggestion."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 45.0,
                        "files_without_tests": 12,
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("code-review")
        workflow_names = [s.workflow_name for s in suggestions]
        assert "test-gen" in workflow_names

    def test_skips_test_gen_when_already_running(self, tmp_path, monkeypatch):
        """Test doesn't suggest test-gen if that's what just ran."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 30.0,
                        "files_without_tests": 20,
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("test-gen")
        workflow_names = [s.workflow_name for s in suggestions]
        assert "test-gen" not in workflow_names

    def test_stale_files_suggest_test_gen(self, tmp_path, monkeypatch):
        """Test stale tests trigger test-gen suggestion."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 90.0,
                        "stale_file_count": 5,
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("code-review")
        found = [s for s in suggestions if "stale" in s.description.lower()]
        assert len(found) > 0

    def test_critical_untested_suggests_security_audit(self, tmp_path, monkeypatch):
        """Test critical untested files trigger security-audit suggestion."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 90.0,
                        "critical_untested_files": ["auth.py", "crypto.py"],
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("code-review")
        workflow_names = [s.workflow_name for s in suggestions]
        assert "security-audit" in workflow_names

    def test_attention_files_suggest_code_review(self, tmp_path, monkeypatch):
        """Test many attention-needing files trigger code-review suggestion."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 90.0,
                        "files_needing_attention": 8,
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("security-audit")
        workflow_names = [s.workflow_name for s in suggestions]
        assert "code-review" in workflow_names

    def test_no_index_returns_empty(self, tmp_path, monkeypatch):
        """Test missing project index returns empty suggestions."""
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("code-review")
        assert suggestions == []

    def test_healthy_project_returns_empty(self, tmp_path, monkeypatch):
        """Test healthy project returns no index-based suggestions."""
        index_dir = tmp_path / ".attune"
        index_dir.mkdir()
        index_file = index_dir / "project_index.json"
        index_file.write_text(
            json.dumps(
                {
                    "summary": {
                        "test_coverage_avg": 95.0,
                        "files_without_tests": 0,
                        "stale_file_count": 0,
                        "critical_untested_files": [],
                        "files_needing_attention": 0,
                    },
                },
            ),
        )
        monkeypatch.chdir(tmp_path)
        suggestions = _suggestions_from_project_index("code-review")
        assert suggestions == []


# ============================================================================
# WORKFLOW HISTORY PATTERNS
# ============================================================================


class TestWorkflowHistorySignals:
    """Tests for workflow history-based suggestions."""

    def test_detects_follow_up_pattern(self):
        """Test detecting common follow-up workflow patterns."""
        mock_runs = [
            {"workflow_name": "code-review", "started_at": "2026-01-01T10:00:00"},
            {"workflow_name": "security-audit", "started_at": "2026-01-01T10:30:00"},
            {"workflow_name": "code-review", "started_at": "2026-01-02T10:00:00"},
            {"workflow_name": "security-audit", "started_at": "2026-01-02T10:30:00"},
            {"workflow_name": "code-review", "started_at": "2026-01-03T10:00:00"},
            {"workflow_name": "security-audit", "started_at": "2026-01-03T10:30:00"},
        ]

        def mock_get_store():
            class MockStore:
                def query_runs(self, success_only=False, limit=50):
                    return mock_runs

            return MockStore()

        with patch(
            "attune.workflows.history_utils._get_history_store",
            mock_get_store,
        ):
            suggestions = _suggestions_from_history("code-review")
            workflow_names = [s.workflow_name for s in suggestions]
            assert "security-audit" in workflow_names

    def test_ignores_single_occurrence(self):
        """Test that single-occurrence follow-ups are not suggested."""
        mock_runs = [
            {"workflow_name": "code-review", "started_at": "2026-01-01T10:00:00"},
            {"workflow_name": "security-audit", "started_at": "2026-01-01T10:30:00"},
            {"workflow_name": "code-review", "started_at": "2026-01-02T10:00:00"},
            {"workflow_name": "test-gen", "started_at": "2026-01-02T10:30:00"},
        ]

        def mock_get_store():
            class MockStore:
                def query_runs(self, success_only=False, limit=50):
                    return mock_runs

            return MockStore()

        with patch(
            "attune.workflows.history_utils._get_history_store",
            mock_get_store,
        ):
            suggestions = _suggestions_from_history("code-review")
            # Each follow-up only appears once, so none should be suggested
            assert suggestions == []

    def test_no_history_returns_empty(self):
        """Test that no history returns empty suggestions."""

        def mock_get_store():
            return None

        with patch(
            "attune.workflows.history_utils._get_history_store",
            mock_get_store,
        ):
            suggestions = _suggestions_from_history("code-review")
            assert suggestions == []

    def test_history_suggestions_have_low_priority(self):
        """Test that history-based suggestions get low priority."""
        mock_runs = [
            {"workflow_name": "code-review", "started_at": f"2026-01-{i:02d}T10:00:00"}
            for i in range(1, 6)
        ]
        # Interleave with test-gen follow-ups
        interleaved = []
        for i, run in enumerate(mock_runs):
            interleaved.append(run)
            interleaved.append(
                {
                    "workflow_name": "test-gen",
                    "started_at": f"2026-01-{i + 1:02d}T10:30:00",
                },
            )

        def mock_get_store():
            class MockStore:
                def query_runs(self, success_only=False, limit=50):
                    return interleaved

            return MockStore()

        with patch(
            "attune.workflows.history_utils._get_history_store",
            mock_get_store,
        ):
            suggestions = _suggestions_from_history("code-review")
            for s in suggestions:
                assert s.priority == "low"


# ============================================================================
# SUGGESTION PERSISTENCE
# ============================================================================


class TestSuggestionPersistence:
    """Tests for cross-session suggestion persistence."""

    def test_record_and_filter_recent(self, tmp_path, monkeypatch):
        """Test that recently shown suggestions are filtered out."""
        monkeypatch.chdir(tmp_path)
        state_dir = tmp_path / ".attune"
        state_dir.mkdir()

        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage gap",
            ),
            NextAction(
                workflow_name="security-audit",
                description="Run audit",
                reasoning="Found issues",
            ),
        ]

        # Record that these were shown
        record_suggestions_shown(suggestions)

        # Verify state file exists
        state_file = state_dir / "suggestion_state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert "test-gen" in state["dismissed"]
        assert "security-audit" in state["dismissed"]

        # Filter should remove recently-shown suggestions
        filtered = _filter_recently_shown(suggestions)
        assert len(filtered) == 0

    def test_expired_suggestions_reappear(self, tmp_path, monkeypatch):
        """Test that suggestions reappear after dismiss period expires."""
        monkeypatch.chdir(tmp_path)
        state_dir = tmp_path / ".attune"
        state_dir.mkdir()

        # Write state with old timestamp (25 hours ago)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        state_file = state_dir / "suggestion_state.json"
        state_file.write_text(json.dumps({"dismissed": {"test-gen": old_time}}))

        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage gap",
            ),
        ]

        filtered = _filter_recently_shown(suggestions)
        assert len(filtered) == 1
        assert filtered[0].workflow_name == "test-gen"

    def test_no_state_file_passes_all(self, tmp_path, monkeypatch):
        """Test that missing state file doesn't filter anything."""
        monkeypatch.chdir(tmp_path)

        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage gap",
            ),
        ]

        filtered = _filter_recently_shown(suggestions)
        assert len(filtered) == 1

    def test_record_empty_suggestions_is_noop(self, tmp_path, monkeypatch):
        """Test that recording empty list doesn't create state file."""
        monkeypatch.chdir(tmp_path)
        record_suggestions_shown([])
        state_file = tmp_path / ".attune" / "suggestion_state.json"
        assert not state_file.exists()

    def test_partial_filter(self, tmp_path, monkeypatch):
        """Test that only recently-shown suggestions are filtered."""
        monkeypatch.chdir(tmp_path)
        state_dir = tmp_path / ".attune"
        state_dir.mkdir()

        # Only test-gen was recently shown
        recent_time = datetime.now().isoformat()
        state_file = state_dir / "suggestion_state.json"
        state_file.write_text(json.dumps({"dismissed": {"test-gen": recent_time}}))

        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage gap",
            ),
            NextAction(
                workflow_name="security-audit",
                description="Run audit",
                reasoning="Found issues",
            ),
        ]

        filtered = _filter_recently_shown(suggestions)
        assert len(filtered) == 1
        assert filtered[0].workflow_name == "security-audit"
