"""Unit tests for attune.meta_workflows.cli_commands.memory_commands.

Covers search_memory and show_session_stats CLI commands.
Uses Typer's CliRunner with the app declared in cli_commands/__init__.py.

Both commands import their collaborators (UnifiedMemory, SessionContext)
with a LOCAL `from ... import ...` inside the function body, so patches
target the source modules (attune.memory.unified.UnifiedMemory,
attune.meta_workflows.session_context.SessionContext), not the
memory_commands module namespace -- matching the pattern already used
in test_workflow_commands.py for the same style of local import.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app

UNIFIED_MEMORY = "attune.memory.unified.UnifiedMemory"
SESSION_CONTEXT = "attune.meta_workflows.session_context.SessionContext"


@pytest.fixture
def runner():
    return CliRunner()


def _row(output: str, label: str) -> str:
    """Return the single rich-table row line containing `label`.

    Table rows are wrapped in box-drawing bars ("|"); this disambiguates
    a metric row (e.g. "Templates Used") from the separate free-standing
    "Templates Used:" bullet-list heading, which shares the same words.
    """
    lines = [line for line in output.splitlines() if line.startswith("│") and label in line]
    assert len(lines) == 1, f"expected exactly one table row containing {label!r}, got {lines!r}"
    return lines[0]


# ---------------------------------------------------------------------------
# search-memory
# ---------------------------------------------------------------------------


class TestSearchMemory:
    def test_no_results(self, runner):
        """Empty results -> yellow 'no matches' message, no 'Found' text."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = []
            result = runner.invoke(meta_workflow_app, ["search-memory", "nothing"])

        assert result.exit_code == 0
        assert "No matching patterns found." in result.output
        assert "Found" not in result.output

    def test_results_displayed_with_pattern_type_filter(self, runner):
        """Results found + --type filter shown; panel content is exact."""
        pattern = {
            "pattern_id": "p1",
            "pattern_type": "meta_workflow_execution",
            "classification": "success",
            "content": "hello world",
            "metadata": {"k": "v"},
        }
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = [pattern]
            result = runner.invoke(
                meta_workflow_app,
                ["search-memory", "test query", "--type", "meta_workflow_execution"],
            )

        assert result.exit_code == 0
        assert "Pattern type: meta_workflow_execution" in result.output
        assert "Found 1 matching pattern(s):" in result.output
        assert "Pattern ID:" in result.output
        assert "p1" in result.output
        assert "meta_workflow_execution" in result.output
        assert "success" in result.output
        assert "hello world" in result.output
        assert "{'k': 'v'}" in result.output
        MockMem.return_value.search_patterns.assert_called_once_with(
            query="test query",
            pattern_type="meta_workflow_execution",
            limit=10,
        )

    def test_no_pattern_type_filter_omits_dim_line(self, runner):
        """Without --type, the 'Pattern type:' dim line is not printed."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = []
            result = runner.invoke(meta_workflow_app, ["search-memory", "q"])

        assert result.exit_code == 0
        assert "Pattern type:" not in result.output

    def test_defaults_forwarded(self, runner):
        """Default user_id/limit are forwarded to UnifiedMemory/search_patterns."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = []
            runner.invoke(meta_workflow_app, ["search-memory", "q"])

        MockMem.assert_called_once_with(user_id="cli_user")
        MockMem.return_value.search_patterns.assert_called_once_with(
            query="q",
            pattern_type=None,
            limit=10,
        )

    def test_custom_limit_and_user_id(self, runner):
        """--limit and --user-id override the defaults."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = []
            runner.invoke(
                meta_workflow_app,
                ["search-memory", "q", "--limit", "5", "--user-id", "alice"],
            )

        MockMem.assert_called_once_with(user_id="alice")
        MockMem.return_value.search_patterns.assert_called_once_with(
            query="q",
            pattern_type=None,
            limit=5,
        )

    def test_multiple_results_numbered(self, runner):
        """Multiple patterns get numbered 'Result i/N' titles."""
        patterns = [
            {
                "pattern_id": "p1",
                "pattern_type": "t",
                "classification": "c",
                "content": "a",
                "metadata": {},
            },
            {
                "pattern_id": "p2",
                "pattern_type": "t",
                "classification": "c",
                "content": "b",
                "metadata": {},
            },
        ]
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = patterns
            result = runner.invoke(meta_workflow_app, ["search-memory", "q"])

        assert result.exit_code == 0
        assert "Found 2 matching pattern(s):" in result.output
        assert "Result 1/2" in result.output
        assert "Result 2/2" in result.output

    def test_missing_pattern_fields_default_to_na(self, runner):
        """Empty pattern dict -> 'N/A' defaults for id/type/classification."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.return_value = [{}]
            result = runner.invoke(meta_workflow_app, ["search-memory", "q"])

        assert result.exit_code == 0
        # Three fields (id/type/classification) each fall back to 'N/A'; a bare
        # "N/A" in output would be satisfied by a single default, so require all
        # three to prove each field independently fell back.
        assert result.output.count("N/A") >= 3

    def test_import_error_exits_1(self, runner):
        """ImportError while acquiring UnifiedMemory -> exit 1, specific message."""
        with patch(UNIFIED_MEMORY, side_effect=ImportError("no module")):
            result = runner.invoke(meta_workflow_app, ["search-memory", "q"])

        assert result.exit_code == 1
        assert "UnifiedMemory not available" in result.output

    def test_generic_exception_exits_1(self, runner):
        """Unexpected exception -> exit 1, error message includes str(e)."""
        with patch(UNIFIED_MEMORY) as MockMem:
            MockMem.return_value.search_patterns.side_effect = RuntimeError("boom")
            result = runner.invoke(meta_workflow_app, ["search-memory", "q"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "boom" in result.output


# ---------------------------------------------------------------------------
# session-stats
# ---------------------------------------------------------------------------


class TestShowSessionStats:
    def test_full_stats_with_templates(self, runner):
        """Populated stats -> table rows + 'Templates Used:' bullet list."""
        stats = {
            "choice_count": 7,
            "templates_used": ["release-prep", "security-audit"],
            "most_recent_choice_timestamp": "2026-01-01T00:00:00Z",
        }
        with (
            patch(UNIFIED_MEMORY) as MockMem,
            patch(SESSION_CONTEXT) as MockSession,
        ):
            mock_session = MockSession.return_value
            mock_session.session_id = "sess-123"
            mock_session.user_id = "cli_user"
            mock_session.get_session_stats.return_value = stats
            result = runner.invoke(meta_workflow_app, ["session-stats"])

        assert result.exit_code == 0
        assert "Session ID: sess-123" in result.output
        assert "User ID: cli_user" in result.output
        assert "7" in _row(result.output, "Total Choices")
        assert "2" in _row(result.output, "Templates Used")
        assert "2026-01-01T00:00:00Z" in _row(result.output, "Most Recent Choice")
        assert "Templates Used:" in result.output
        assert "release-prep" in result.output
        assert "security-audit" in result.output
        MockSession.assert_called_once_with(memory=MockMem.return_value, session_id=None)

    def test_no_templates_used_omits_heading(self, runner):
        """Empty templates_used -> no 'Templates Used:' bullet heading."""
        stats = {
            "choice_count": 0,
            "templates_used": [],
            "most_recent_choice_timestamp": "N/A",
        }
        with (
            patch(UNIFIED_MEMORY),
            patch(SESSION_CONTEXT) as MockSession,
        ):
            mock_session = MockSession.return_value
            mock_session.session_id = "sess-1"
            mock_session.user_id = "cli_user"
            mock_session.get_session_stats.return_value = stats
            result = runner.invoke(meta_workflow_app, ["session-stats"])

        assert result.exit_code == 0
        assert "Templates Used:" not in result.output

    def test_missing_stats_fields_default(self, runner):
        """Empty stats dict -> choice_count 0, templates 0, timestamp N/A."""
        with (
            patch(UNIFIED_MEMORY),
            patch(SESSION_CONTEXT) as MockSession,
        ):
            mock_session = MockSession.return_value
            mock_session.session_id = "sess-1"
            mock_session.user_id = "cli_user"
            mock_session.get_session_stats.return_value = {}
            result = runner.invoke(meta_workflow_app, ["session-stats"])

        assert result.exit_code == 0
        assert "0" in _row(result.output, "Total Choices")
        assert "0" in _row(result.output, "Templates Used")
        assert "N/A" in _row(result.output, "Most Recent Choice")
        assert "Templates Used:" not in result.output

    def test_custom_session_id_and_user_id_forwarded(self, runner):
        """--session-id and --user-id are forwarded to the constructors."""
        with (
            patch(UNIFIED_MEMORY) as MockMem,
            patch(SESSION_CONTEXT) as MockSession,
        ):
            mock_session = MockSession.return_value
            mock_session.session_id = "sess_123"
            mock_session.user_id = "alice"
            mock_session.get_session_stats.return_value = {}
            runner.invoke(
                meta_workflow_app,
                ["session-stats", "--session-id", "sess_123", "--user-id", "alice"],
            )

        MockMem.assert_called_once_with(user_id="alice")
        MockSession.assert_called_once_with(memory=MockMem.return_value, session_id="sess_123")

    def test_import_error_exits_1(self, runner):
        """ImportError while acquiring UnifiedMemory -> exit 1, specific message."""
        with patch(UNIFIED_MEMORY, side_effect=ImportError("no module")):
            result = runner.invoke(meta_workflow_app, ["session-stats"])

        assert result.exit_code == 1
        assert "Session context not available" in result.output

    def test_generic_exception_exits_1(self, runner):
        """Unexpected exception -> exit 1, error message includes str(e)."""
        with (
            patch(UNIFIED_MEMORY),
            patch(SESSION_CONTEXT) as MockSession,
        ):
            MockSession.return_value.get_session_stats.side_effect = RuntimeError("kaboom")
            result = runner.invoke(meta_workflow_app, ["session-stats"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "kaboom" in result.output
