"""Unit tests for MCP help-related handlers.

Tests cover:
- _sanitize_prompt_arg: input sanitization for prompt interpolation
- _handle_help_lookup: four help modes (progressive, workflow_help,
  precursor, search_tag) plus unknown-mode error
- _handle_help_maintain: delegating to HelpMaintenanceWorkflow

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.prompts import _sanitize_prompt_arg

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


@dataclass
class _FakePopulated:
    """Minimal stand-in for PopulatedTemplate."""

    title: str = "Title"
    body: str = "Body"
    type: str = "concept"
    tags: list[str] = field(default_factory=list)
    related: list[dict[str, str]] = field(default_factory=list)
    template_id: str = "tpl-1"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeWorkflowResult:
    """Minimal stand-in for WorkflowResult."""

    success: bool = True
    final_output: str = "maintenance done"


def _make_server(tmp_path: Any) -> Any:
    """Build an EmpathyMCPServer pointed at a temp workspace.

    Patches heavyweight init side-effects (plugin discovery)
    to keep the test fast. The version-check thread is a daemon
    inside a try/except and is harmless.
    """
    with patch(
        "attune.mcp.server.EmpathyMCPServer._register_plugin_tools",
    ):
        from attune.mcp.server import EmpathyMCPServer

        return EmpathyMCPServer(workspace_root=str(tmp_path))


# ------------------------------------------------------------------
# _sanitize_prompt_arg
# ------------------------------------------------------------------


@pytest.mark.unit
class TestSanitizePromptArg:
    """Tests for _sanitize_prompt_arg function."""

    def test_strips_backticks(self) -> None:
        """Backticks are removed to prevent code fence injection."""
        assert _sanitize_prompt_arg("hello`world`") == "helloworld"

    def test_strips_newlines(self) -> None:
        """Newline characters are removed."""
        assert _sanitize_prompt_arg("line1\nline2") == "line1line2"

    def test_strips_carriage_returns(self) -> None:
        """Carriage return characters are removed."""
        assert _sanitize_prompt_arg("line1\rline2") == "line1line2"

    def test_strips_control_chars(self) -> None:
        """ASCII control characters (0x00-0x1f) are removed."""
        assert _sanitize_prompt_arg("a\x00b\x01c\x1fd") == "abcd"

    def test_truncates_to_500(self) -> None:
        """Values longer than 500 characters are truncated."""
        long = "x" * 1000
        result = _sanitize_prompt_arg(long)
        assert len(result) == 500

    def test_preserves_normal_text(self) -> None:
        """Normal alphanumeric and punctuation text passes through."""
        text = "Hello, world! This is fine."
        assert _sanitize_prompt_arg(text) == text

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert _sanitize_prompt_arg("") == ""

    def test_combined_stripping_and_truncation(self) -> None:
        """Stripping happens before truncation."""
        # 501 'a' chars interspersed with backticks; after strip
        # we get 501 'a' chars, then truncated to 500.
        text = "`" + "a" * 501
        result = _sanitize_prompt_arg(text)
        assert result == "a" * 500


# ------------------------------------------------------------------
# _handle_help_lookup
# ------------------------------------------------------------------

_ENGINE = "attune.mcp.server"
_HELP_IMPORTS = "attune.help.engine"


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleHelpLookup:
    """Tests for EmpathyMCPServer._handle_help_lookup."""

    async def test_progressive_returns_template(self, tmp_path: Any) -> None:
        """Progressive mode returns populated template fields."""
        server = _make_server(tmp_path)

        fake = _FakePopulated(
            title="My Title",
            body="Some body",
            type="concept",
            tags=["t1"],
            related=[{"id": "r1"}],
            metadata={
                "depth_level": 0,
                "level_label": "Concept",
                "topic": "security",
            },
        )

        with patch(
            f"{_HELP_IMPORTS}.populate_progressive",
            return_value=fake,
        ):
            result = await server._handle_help_lookup(
                {"topic": "security", "mode": "progressive"},
            )

        assert result["success"] is True
        assert result["title"] == "My Title"
        assert result["body"] == "Some body"
        assert result["type"] == "concept"
        assert result["depth_level"] == 0
        assert result["level_label"] == "Concept"
        assert result["topic"] == "security"
        assert result["tags"] == ["t1"]
        assert result["related"] == [{"id": "r1"}]

    async def test_progressive_not_found(self, tmp_path: Any) -> None:
        """Progressive mode returns error when template is missing."""
        server = _make_server(tmp_path)

        with patch(
            f"{_HELP_IMPORTS}.populate_progressive",
            return_value=None,
        ):
            result = await server._handle_help_lookup(
                {"topic": "nonexistent"},
            )

        assert result["success"] is False
        assert "nonexistent" in result["error"]

    async def test_progressive_reset_calls_reset_session(self, tmp_path: Any) -> None:
        """When reset=True, reset_session is called before lookup."""
        server = _make_server(tmp_path)

        mock_reset = MagicMock()
        fake = _FakePopulated()

        with (
            patch(f"{_HELP_IMPORTS}.reset_session", mock_reset),
            patch(
                f"{_HELP_IMPORTS}.populate_progressive",
                return_value=fake,
            ),
        ):
            await server._handle_help_lookup(
                {"topic": "x", "mode": "progressive", "reset": True},
            )

        mock_reset.assert_called_once()

    async def test_progressive_last_workflow_sets_starting_level(self, tmp_path: Any) -> None:
        """When last_workflow is set, starting_level is passed as 1."""
        server = _make_server(tmp_path)

        fake = _FakePopulated()
        mock_pop = MagicMock(return_value=fake)

        with patch(f"{_HELP_IMPORTS}.populate_progressive", mock_pop):
            await server._handle_help_lookup(
                {
                    "topic": "x",
                    "mode": "progressive",
                    "last_workflow": "code-review",
                },
            )

        _, kwargs = mock_pop.call_args
        assert kwargs["starting_level"] == 1

    async def test_workflow_help_returns_templates(self, tmp_path: Any) -> None:
        """workflow_help mode returns list of template summaries."""
        server = _make_server(tmp_path)

        templates = [
            _FakePopulated(title="T1", body="B1", template_id="id1"),
            _FakePopulated(title="T2", body="B2", template_id="id2"),
        ]

        with patch(
            f"{_HELP_IMPORTS}.get_workflow_help",
            return_value=templates,
        ):
            result = await server._handle_help_lookup(
                {"topic": "code-review", "mode": "workflow_help"},
            )

        assert result["success"] is True
        assert len(result["templates"]) == 2
        assert result["templates"][0]["title"] == "T1"
        assert result["templates"][1]["id"] == "id2"

    async def test_precursor_returns_warnings(self, tmp_path: Any) -> None:
        """Precursor mode returns warning list."""
        server = _make_server(tmp_path)

        warnings = [
            _FakePopulated(title="W1", body="B1", template_id="w1"),
        ]

        with patch(
            f"{_HELP_IMPORTS}.get_precursor_warnings",
            return_value=warnings,
        ):
            result = await server._handle_help_lookup(
                {"topic": "config.py", "mode": "precursor"},
            )

        assert result["success"] is True
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["title"] == "W1"

    async def test_precursor_uses_file_path_arg(self, tmp_path: Any) -> None:
        """Precursor mode prefers file_path over topic."""
        server = _make_server(tmp_path)

        mock_fn = MagicMock(return_value=[])

        with patch(f"{_HELP_IMPORTS}.get_precursor_warnings", mock_fn):
            await server._handle_help_lookup(
                {
                    "topic": "fallback",
                    "mode": "precursor",
                    "file_path": "src/foo.py",
                },
            )

        mock_fn.assert_called_once_with("src/foo.py")

    async def test_precursor_falls_back_to_topic(self, tmp_path: Any) -> None:
        """Precursor mode uses topic when file_path is absent."""
        server = _make_server(tmp_path)

        mock_fn = MagicMock(return_value=[])

        with patch(f"{_HELP_IMPORTS}.get_precursor_warnings", mock_fn):
            await server._handle_help_lookup(
                {"topic": "server.py", "mode": "precursor"},
            )

        mock_fn.assert_called_once_with("server.py")

    async def test_search_tag_returns_ids(self, tmp_path: Any) -> None:
        """search_tag mode returns template IDs and count."""
        server = _make_server(tmp_path)

        with patch(
            f"{_HELP_IMPORTS}.search_by_tag",
            return_value=["id-a", "id-b", "id-c"],
        ):
            result = await server._handle_help_lookup(
                {"topic": "security", "mode": "search_tag"},
            )

        assert result["success"] is True
        assert result["template_ids"] == ["id-a", "id-b", "id-c"]
        assert result["count"] == 3

    async def test_unknown_mode_returns_error(self, tmp_path: Any) -> None:
        """Unknown mode returns an error dict."""
        server = _make_server(tmp_path)

        result = await server._handle_help_lookup(
            {"topic": "x", "mode": "bogus"},
        )

        assert result["success"] is False
        assert "bogus" in result["error"]

    async def test_default_mode_is_progressive(self, tmp_path: Any) -> None:
        """When mode is omitted, progressive is used."""
        server = _make_server(tmp_path)

        fake = _FakePopulated()
        mock_pop = MagicMock(return_value=fake)

        with patch(f"{_HELP_IMPORTS}.populate_progressive", mock_pop):
            result = await server._handle_help_lookup(
                {"topic": "anything"},
            )

        assert result["success"] is True
        mock_pop.assert_called_once()


# ------------------------------------------------------------------
# _handle_help_maintain
# ------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleHelpMaintain:
    """Tests for EmpathyMCPServer._handle_help_maintain."""

    async def test_delegates_to_workflow(self, tmp_path: Any) -> None:
        """Handler creates workflow and calls execute."""
        server = _make_server(tmp_path)

        fake_result = _FakeWorkflowResult(success=True, final_output="ok")
        mock_wf = MagicMock()
        mock_wf.execute = AsyncMock(return_value=fake_result)

        with patch(
            "attune.workflows.help_maintenance" ".HelpMaintenanceWorkflow",
            return_value=mock_wf,
        ):
            result = await server._handle_help_maintain({})

        mock_wf.execute.assert_awaited_once_with(dry_run=False, batch=False)
        assert result["success"] is True
        assert result["output"] == "ok"

    async def test_dry_run_forwarded(self, tmp_path: Any) -> None:
        """dry_run=True is forwarded to workflow.execute."""
        server = _make_server(tmp_path)

        fake_result = _FakeWorkflowResult(success=True)
        mock_wf = MagicMock()
        mock_wf.execute = AsyncMock(return_value=fake_result)

        with patch(
            "attune.workflows.help_maintenance" ".HelpMaintenanceWorkflow",
            return_value=mock_wf,
        ):
            await server._handle_help_maintain({"dry_run": True})

        mock_wf.execute.assert_awaited_once_with(dry_run=True, batch=False)

    async def test_batch_forwarded(self, tmp_path: Any) -> None:
        """batch=True is forwarded to workflow.execute."""
        server = _make_server(tmp_path)

        fake_result = _FakeWorkflowResult(success=True)
        mock_wf = MagicMock()
        mock_wf.execute = AsyncMock(return_value=fake_result)

        with patch(
            "attune.workflows.help_maintenance" ".HelpMaintenanceWorkflow",
            return_value=mock_wf,
        ):
            await server._handle_help_maintain({"batch": True})

        mock_wf.execute.assert_awaited_once_with(dry_run=False, batch=True)

    async def test_failure_propagated(self, tmp_path: Any) -> None:
        """Workflow failure is reflected in the result dict."""
        server = _make_server(tmp_path)

        fake_result = _FakeWorkflowResult(success=False, final_output="error details")
        mock_wf = MagicMock()
        mock_wf.execute = AsyncMock(return_value=fake_result)

        with patch(
            "attune.workflows.help_maintenance" ".HelpMaintenanceWorkflow",
            return_value=mock_wf,
        ):
            result = await server._handle_help_maintain({})

        assert result["success"] is False
        assert result["output"] == "error details"
