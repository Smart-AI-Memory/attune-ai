"""Tests for suggestions.py — transition functions and engine.

Covers the uncovered transition functions and the main
generate_suggestions engine including failure paths,
history, project index, and formatting.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.workflows.data_classes import NextAction
from attune.workflows.suggestions import (
    _extract_output_text,
    _transitions_for_bug_predict,
    _transitions_for_dependency_check,
    _transitions_for_perf_audit,
    _transitions_for_refactor_plan,
    _transitions_for_simplify_code,
    _transitions_for_test_gen,
    format_suggestions_markdown,
    generate_suggestions,
    suggestions_to_options,
)


def _make_result(
    success: bool = True,
    final_output: str = "",
    transient: bool = False,
    error_type: str | None = None,
) -> MagicMock:
    """Create a mock WorkflowResult."""
    r = MagicMock()
    r.success = success
    r.final_output = final_output
    r.transient = transient
    r.error_type = error_type
    return r


class TestTransitionsForTestGen:
    """Test _transitions_for_test_gen."""

    def test_success_suggests_code_review(self):
        result = _make_result(success=True)
        suggestions = _transitions_for_test_gen(result)
        assert len(suggestions) == 1
        assert suggestions[0].workflow_name == "code-review"

    def test_failure_returns_empty(self):
        result = _make_result(success=False)
        suggestions = _transitions_for_test_gen(result)
        assert len(suggestions) == 0


class TestTransitionsForPerfAudit:
    """Test _transitions_for_perf_audit."""

    def test_success_with_output_suggests_simplify(self):
        result = _make_result(success=True, final_output="Found bottleneck in parser")
        suggestions = _transitions_for_perf_audit(result)
        assert len(suggestions) == 1
        assert suggestions[0].workflow_name == "simplify-code"

    def test_failure_returns_empty(self):
        result = _make_result(success=False, final_output="error")
        suggestions = _transitions_for_perf_audit(result)
        assert len(suggestions) == 0

    def test_success_no_output_returns_empty(self):
        result = _make_result(success=True, final_output="")
        suggestions = _transitions_for_perf_audit(result)
        assert len(suggestions) == 0


class TestTransitionsForRefactorPlan:
    """Test _transitions_for_refactor_plan."""

    def test_success_suggests_test_gen(self):
        result = _make_result(success=True)
        suggestions = _transitions_for_refactor_plan(result)
        assert len(suggestions) == 1
        assert suggestions[0].workflow_name == "test-gen"
        assert suggestions[0].priority == "high"

    def test_failure_returns_empty(self):
        result = _make_result(success=False)
        suggestions = _transitions_for_refactor_plan(result)
        assert len(suggestions) == 0


class TestTransitionsForSimplifyCode:
    """Test _transitions_for_simplify_code."""

    def test_success_suggests_code_review(self):
        result = _make_result(success=True)
        suggestions = _transitions_for_simplify_code(result)
        assert len(suggestions) == 1
        assert suggestions[0].workflow_name == "code-review"

    def test_failure_returns_empty(self):
        result = _make_result(success=False)
        suggestions = _transitions_for_simplify_code(result)
        assert len(suggestions) == 0


class TestTransitionsForDependencyCheck:
    """Test _transitions_for_dependency_check."""

    def test_outdated_deps_suggest_test_gen(self):
        result = _make_result(
            success=True,
            final_output="3 packages have update available, 1 deprecated",
        )
        suggestions = _transitions_for_dependency_check(result)
        assert len(suggestions) == 1
        assert suggestions[0].workflow_name == "test-gen"

    def test_no_outdated_returns_empty(self):
        result = _make_result(success=True, final_output="All dependencies up to date")
        suggestions = _transitions_for_dependency_check(result)
        assert len(suggestions) == 0


class TestTransitionsForBugPredict:
    """Test _transitions_for_bug_predict."""

    def test_high_risk_suggests_test_gen(self):
        result = _make_result(
            success=True,
            final_output="Found 3 high risk areas with likely bug patterns",
        )
        suggestions = _transitions_for_bug_predict(result)
        names = [s.workflow_name for s in suggestions]
        assert "test-gen" in names

    def test_complexity_suggests_refactor(self):
        result = _make_result(
            success=True,
            final_output="Deeply nested code with high complexity score",
        )
        suggestions = _transitions_for_bug_predict(result)
        names = [s.workflow_name for s in suggestions]
        assert "refactor-plan" in names

    def test_clean_output_returns_empty(self):
        result = _make_result(success=True, final_output="No issues found")
        suggestions = _transitions_for_bug_predict(result)
        assert len(suggestions) == 0


class TestGenerateSuggestions:
    """Test the main generate_suggestions engine."""

    @patch("attune.workflows.suggestions.record_suggestions_shown")
    @patch("attune.workflows.suggestions._filter_recently_shown", side_effect=lambda x: x)
    @patch("attune.workflows.suggestions._suggestions_from_history", return_value=[])
    @patch("attune.workflows.suggestions._suggestions_from_project_index", return_value=[])
    def test_success_uses_transition_registry(self, mock_idx, mock_hist, mock_filter, mock_record):
        result = _make_result(success=True, final_output="Found security vulnerability")
        suggestions = generate_suggestions("code-review", result)
        assert isinstance(suggestions, list)
        # Should find security-audit suggestion from keywords
        names = [s.workflow_name for s in suggestions]
        assert "security-audit" in names

    @patch("attune.workflows.suggestions.record_suggestions_shown")
    @patch("attune.workflows.suggestions._filter_recently_shown", side_effect=lambda x: x)
    @patch("attune.workflows.suggestions._suggestions_from_history", return_value=[])
    @patch("attune.workflows.suggestions._suggestions_from_project_index", return_value=[])
    def test_failure_returns_failure_suggestions(
        self, mock_idx, mock_hist, mock_filter, mock_record
    ):
        result = _make_result(success=False, transient=True, error_type="config")
        suggestions = generate_suggestions("code-review", result)
        # Should get retry suggestion for transient error
        names = [s.workflow_name for s in suggestions]
        assert "code-review" in names  # retry

    @patch("attune.workflows.suggestions.record_suggestions_shown")
    @patch("attune.workflows.suggestions._filter_recently_shown", side_effect=lambda x: x)
    @patch("attune.workflows.suggestions._suggestions_from_history", return_value=[])
    @patch("attune.workflows.suggestions._suggestions_from_project_index", return_value=[])
    def test_config_error_suggests_dependency_check(
        self, mock_idx, mock_hist, mock_filter, mock_record
    ):
        result = _make_result(success=False, transient=False, error_type="config")
        suggestions = generate_suggestions("test-gen", result)
        names = [s.workflow_name for s in suggestions]
        assert "dependency-check" in names

    @patch("attune.workflows.suggestions.record_suggestions_shown")
    @patch("attune.workflows.suggestions._filter_recently_shown", side_effect=lambda x: x)
    @patch("attune.workflows.suggestions._suggestions_from_history", return_value=[])
    @patch("attune.workflows.suggestions._suggestions_from_project_index", return_value=[])
    def test_max_suggestions_limit(self, mock_idx, mock_hist, mock_filter, mock_record):
        result = _make_result(
            success=True,
            final_output=(
                "security vulnerability injection xss path traversal "
                "performance slow bottleneck optimize"
            ),
        )
        suggestions = generate_suggestions("code-review", result)
        assert len(suggestions) <= 3

    @patch("attune.workflows.suggestions.record_suggestions_shown")
    @patch("attune.workflows.suggestions._filter_recently_shown", side_effect=lambda x: x)
    @patch("attune.workflows.suggestions._suggestions_from_history", return_value=[])
    @patch("attune.workflows.suggestions._suggestions_from_project_index", return_value=[])
    def test_unknown_workflow_returns_empty(self, mock_idx, mock_hist, mock_filter, mock_record):
        result = _make_result(success=True, final_output="nothing interesting")
        suggestions = generate_suggestions("unknown-workflow", result)
        assert isinstance(suggestions, list)


class TestFormatSuggestionsMarkdown:
    """Test format_suggestions_markdown."""

    def test_empty_returns_empty(self):
        assert format_suggestions_markdown([]) == ""

    def test_single_suggestion(self):
        suggestions = [
            NextAction(
                workflow_name="test-gen",
                description="Generate tests",
                reasoning="Coverage is low",
                priority="high",
                confidence=0.9,
            ),
        ]
        md = format_suggestions_markdown(suggestions)
        assert "## What's Next" in md
        assert "`/test-gen`" in md
        assert "Generate tests" in md

    def test_multiple_priorities(self):
        suggestions = [
            NextAction(
                workflow_name="security-audit",
                description="Run audit",
                reasoning="Reason",
                priority="high",
                confidence=0.9,
            ),
            NextAction(
                workflow_name="test-gen",
                description="Write tests",
                reasoning="Reason",
                priority="low",
                confidence=0.5,
            ),
        ]
        md = format_suggestions_markdown(suggestions)
        assert "1." in md
        assert "2." in md


class TestSuggestionsToOptions:
    """Test suggestions_to_options."""

    def test_empty_returns_empty(self):
        assert suggestions_to_options([]) == []

    def test_converts_to_option_dicts(self):
        suggestions = [
            NextAction(
                workflow_name="code-review",
                description="Review code",
                reasoning="Reason",
                priority="medium",
                confidence=0.7,
            ),
        ]
        options = suggestions_to_options(suggestions)
        assert len(options) == 1
        assert options[0]["label"] == "/code-review"
        assert options[0]["description"] == "Review code"


class TestExtractOutputText:
    """Test _extract_output_text helper."""

    def test_string_input(self):
        assert _extract_output_text("Hello World") == "hello world"

    def test_dict_input(self):
        result = _extract_output_text({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_none_input(self):
        assert _extract_output_text(None) == ""

    def test_numeric_input(self):
        assert _extract_output_text(42) == "42"
