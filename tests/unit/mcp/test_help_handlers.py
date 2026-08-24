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
    """Build an AttuneMCPServer pointed at a temp workspace.

    Patches heavyweight init side-effects (plugin discovery)
    to keep the test fast. The version-check thread is a daemon
    inside a try/except and is harmless.
    """
    with patch(
        "attune.mcp.server.AttuneMCPServer._register_plugin_tools",
    ):
        from attune.mcp.server import AttuneMCPServer

        return AttuneMCPServer(workspace_root=str(tmp_path))


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
    """Tests for AttuneMCPServer._handle_help_lookup."""

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
    """Tests for AttuneMCPServer._handle_help_maintain."""

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


# ------------------------------------------------------------------
# _handle_help_init
# ------------------------------------------------------------------

_BOOT = "attune.help.bootstrap"
_GEN = "attune.help.generator"
_MAN = "attune.help.manifest"
_PREAM = "attune.help.preamble"
_MAINT = "attune.help.maintenance"
_STALE = "attune.help.staleness"
_SEC = "attune.security.path_validation"


@dataclass
class _FakeProposal:
    """Stand-in for ProposedFeature."""

    name: str = "auth"
    description: str = "Authentication"
    files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.9
    reason: str = "heuristic"


@dataclass
class _FakeFeature:
    """Stand-in for manifest Feature."""

    name: str = "auth"
    description: str = "Auth"
    files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class _FakeManifest:
    """Stand-in for FeatureManifest."""

    version: int = 1
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeGenResult:
    """Stand-in for generator result."""

    feature: str = "auth"
    templates: list[str] = field(default_factory=lambda: ["concept.md"])
    matched_files: list[str] = field(default_factory=lambda: ["src/auth.py"])


@dataclass
class _FakeMaintenanceResult:
    """Stand-in for MaintenanceResult."""

    stale_count: int = 1
    regenerated_count: int = 1
    regenerated: list[Any] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


@dataclass
class _FakeStalenessReport:
    """Stand-in for StalenessReport."""

    stale_count: int = 1
    current_count: int = 2
    stale_features: list[str] = field(default_factory=lambda: ["auth"])


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleHelpInit:
    """Tests for _handle_help_init()."""

    async def test_scan_returns_proposals(self, tmp_path: Any) -> None:
        """Scan action returns discovered proposals."""
        server = _make_server(tmp_path)
        proposal = _FakeProposal(name="auth", description="Auth")
        with (
            patch(f"{_BOOT}.scan_project", return_value=[proposal]),
            patch(f"{_SEC}._validate_file_path"),
        ):
            result = await server._handle_help_init({"action": "scan"})
        assert result["success"] is True
        assert result["count"] == 1
        assert result["proposals"][0]["name"] == "auth"

    async def test_accept_saves_and_generates(self, tmp_path: Any) -> None:
        """Accept action saves manifest and generates templates."""
        server = _make_server(tmp_path)
        manifest = _FakeManifest(features={"auth": _FakeFeature()})
        gen_result = _FakeGenResult()
        with (
            patch(f"{_BOOT}.proposals_to_manifest", return_value=manifest),
            patch(f"{_MAN}.save_manifest"),
            patch(f"{_GEN}.generate_feature_templates", return_value=gen_result),
            patch(f"{_PREAM}.get_preamble", return_value="Use auth when..."),
            patch(f"{_SEC}._validate_file_path"),
            patch(f"{_BOOT}.ProposedFeature", _FakeProposal),
        ):
            result = await server._handle_help_init(
                {
                    "action": "accept",
                    "accepted": [{"name": "auth", "description": "Auth"}],
                }
            )
        assert result["success"] is True
        assert result["features"] == 1
        assert result["generated"][0]["preamble"] == "Use auth when..."

    async def test_accept_missing_name_returns_error(self, tmp_path: Any) -> None:
        """Accept rejects proposals without a name."""
        server = _make_server(tmp_path)
        with patch(f"{_SEC}._validate_file_path"):
            result = await server._handle_help_init(
                {
                    "action": "accept",
                    "accepted": [{"description": "no name"}],
                }
            )
        assert result["success"] is False
        assert "name" in result["error"]

    async def test_accept_generation_failure(self, tmp_path: Any) -> None:
        """Generation failure lands in the failed list."""
        server = _make_server(tmp_path)
        manifest = _FakeManifest(features={"auth": _FakeFeature()})
        with (
            patch(f"{_BOOT}.proposals_to_manifest", return_value=manifest),
            patch(f"{_MAN}.save_manifest"),
            patch(f"{_GEN}.generate_feature_templates", side_effect=OSError("disk")),
            patch(f"{_SEC}._validate_file_path"),
            patch(f"{_BOOT}.ProposedFeature", _FakeProposal),
        ):
            result = await server._handle_help_init(
                {
                    "action": "accept",
                    "accepted": [{"name": "auth", "description": "Auth"}],
                }
            )
        assert result["success"] is True
        assert "auth" in result["failed"]

    async def test_unknown_action_returns_error(self, tmp_path: Any) -> None:
        """Unknown action returns an error."""
        server = _make_server(tmp_path)
        with patch(f"{_SEC}._validate_file_path"):
            result = await server._handle_help_init({"action": "bogus"})
        assert result["success"] is False
        assert "bogus" in result["error"]


# ------------------------------------------------------------------
# _handle_help_status
# ------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleHelpStatus:
    """Tests for _handle_help_status()."""

    async def test_returns_staleness_report(self, tmp_path: Any) -> None:
        """Returns stale/current counts and formatted report."""
        server = _make_server(tmp_path)
        report = _FakeStalenessReport()
        with (
            patch(f"{_MAN}.load_manifest", return_value=_FakeManifest()),
            patch(f"{_STALE}.check_staleness", return_value=report),
            patch(f"{_MAINT}.format_status_report", return_value="## Status"),
            patch(f"{_SEC}._validate_file_path"),
        ):
            result = await server._handle_help_status({})
        assert result["success"] is True
        assert result["stale_count"] == 1
        assert result["current_count"] == 2
        assert result["report"] == "## Status"

    async def test_missing_manifest_returns_error(self, tmp_path: Any) -> None:
        """Returns error when features.yaml is absent."""
        server = _make_server(tmp_path)
        with (
            patch(f"{_MAN}.load_manifest", side_effect=FileNotFoundError),
            patch(f"{_SEC}._validate_file_path"),
        ):
            result = await server._handle_help_status({})
        assert result["success"] is False
        assert "help_init" in result["error"]

    async def test_features_filter_forwarded(self, tmp_path: Any) -> None:
        """Features list is forwarded to check_staleness."""
        server = _make_server(tmp_path)
        mock_check = MagicMock(return_value=_FakeStalenessReport())
        with (
            patch(f"{_MAN}.load_manifest", return_value=_FakeManifest()),
            patch(f"{_STALE}.check_staleness", mock_check),
            patch(f"{_MAINT}.format_status_report", return_value=""),
            patch(f"{_SEC}._validate_file_path"),
        ):
            await server._handle_help_status({"features": ["auth"]})
        assert mock_check.call_args[0][3] == ["auth"]


# ------------------------------------------------------------------
# _handle_help_update
# ------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleHelpUpdate:
    """Tests for _handle_help_update()."""

    async def test_successful_regeneration(self, tmp_path: Any) -> None:
        """Returns regeneration results with preambles."""
        server = _make_server(tmp_path)
        maint_result = _FakeMaintenanceResult(
            regenerated=[_FakeGenResult()],
        )
        with (
            patch(f"{_MAINT}.run_maintenance", return_value=maint_result),
            patch(f"{_PREAM}.get_preamble", return_value="preamble text"),
            patch(f"{_SEC}._validate_file_path"),
        ):
            result = await server._handle_help_update({})
        assert result["success"] is True
        assert result["regenerated_count"] == 1
        assert result["regenerated"][0]["preamble"] == "preamble text"

    async def test_dry_run_forwarded(self, tmp_path: Any) -> None:
        """dry_run flag is forwarded to run_maintenance."""
        server = _make_server(tmp_path)
        mock_maint = MagicMock(return_value=_FakeMaintenanceResult())
        with (
            patch(f"{_MAINT}.run_maintenance", mock_maint),
            patch(f"{_SEC}._validate_file_path"),
        ):
            await server._handle_help_update({"dry_run": True})
        assert mock_maint.call_args[1]["dry_run"] is True

    async def test_missing_manifest_returns_error(self, tmp_path: Any) -> None:
        """Returns error when maintenance raises FileNotFoundError."""
        server = _make_server(tmp_path)
        with (
            patch(f"{_MAINT}.run_maintenance", side_effect=FileNotFoundError),
            patch(f"{_SEC}._validate_file_path"),
        ):
            result = await server._handle_help_update({})
        assert result["success"] is False
        assert "help_init" in result["error"]


# ------------------------------------------------------------------
# Unmatched-query logging (FAQ-Generator channel 1)
# ------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHelpLookupUnmatchedLogging:
    """_handle_help_lookup appends unmatched queries to the channel-1 log."""

    @pytest.fixture(autouse=True)
    def _telemetry_on(self, monkeypatch: Any) -> None:
        """Re-enable help telemetry — the global conftest disables it."""
        monkeypatch.delenv("ATTUNE_HELP_TELEMETRY", raising=False)

    def _tracker(self, tmp_path: Any) -> Any:
        from attune.telemetry.help_tracker import HelpTracker

        return HelpTracker(log_dir=tmp_path / "telemetry")

    @staticmethod
    def _events(tracker: Any) -> list[dict[str, Any]]:
        import json

        if not tracker.unmatched_path.exists():
            return []
        return [
            json.loads(line)
            for line in tracker.unmatched_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    async def test_progressive_not_found_logs_unmatched(self, tmp_path: Any) -> None:
        """A template miss appends the raw query to the unmatched log."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(f"{_HELP_IMPORTS}.populate_progressive", return_value=None),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
        ):
            await server._handle_help_lookup({"topic": "how do I frobnicate"})

        events = self._events(tracker)
        assert len(events) == 1
        assert events[0]["query"] == "how do I frobnicate"
        assert events[0]["mode"] == "progressive"
        assert events[0]["source"] == "help_lookup"

    async def test_preamble_not_found_logs_unmatched(self, tmp_path: Any) -> None:
        """A preamble miss appends the raw query to the unmatched log."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(f"{_HELP_IMPORTS}.get_preamble", return_value=None),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
        ):
            await server._handle_help_lookup({"topic": "mystery", "mode": "preamble"})

        events = self._events(tracker)
        assert len(events) == 1
        assert events[0]["query"] == "mystery"
        assert events[0]["mode"] == "preamble"

    async def test_search_tag_zero_hits_logs_unmatched(self, tmp_path: Any) -> None:
        """A tag search with zero hits counts as unmatched."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(f"{_HELP_IMPORTS}.search_by_tag", return_value=[]),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
        ):
            await server._handle_help_lookup({"topic": "no-such-tag", "mode": "search_tag"})

        events = self._events(tracker)
        assert len(events) == 1
        assert events[0]["query"] == "no-such-tag"

    async def test_search_tag_with_hits_not_logged(self, tmp_path: Any) -> None:
        """A tag search with hits is NOT unmatched."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(f"{_HELP_IMPORTS}.search_by_tag", return_value=["tpl-1"]),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
        ):
            await server._handle_help_lookup({"topic": "security", "mode": "search_tag"})

        assert self._events(tracker) == []

    async def test_found_progressive_not_logged(self, tmp_path: Any) -> None:
        """A successful lookup is NOT unmatched."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(f"{_HELP_IMPORTS}.populate_progressive", return_value=_FakePopulated()),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
        ):
            await server._handle_help_lookup({"topic": "security"})

        assert self._events(tracker) == []

    async def test_unknown_mode_not_logged(self, tmp_path: Any) -> None:
        """A caller bug (unknown mode) is NOT a channel-1 signal."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker):
            await server._handle_help_lookup({"topic": "x", "mode": "bogus"})

        assert self._events(tracker) == []

    async def test_impl_exception_not_logged(self, tmp_path: Any) -> None:
        """An error during lookup is NOT unmatched — only resolved misses."""
        server = _make_server(tmp_path)
        tracker = self._tracker(tmp_path)
        with (
            patch(
                f"{_HELP_IMPORTS}.populate_progressive",
                side_effect=RuntimeError("boom"),
            ),
            patch("attune.telemetry.help_tracker.get_tracker", return_value=tracker),
            pytest.raises(RuntimeError),
        ):
            await server._handle_help_lookup({"topic": "x"})

        assert self._events(tracker) == []


@pytest.mark.unit
class TestHelpInitValidatesBeforeSave:
    """Library-review M1: help_init accept must reject an invalid
    feature name BEFORE save_manifest writes it, so one bad entry
    cannot poison the persisted manifest."""

    async def test_traversal_name_rejected_and_manifest_not_written(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        help_dir = tmp_path / ".help"
        result = await server._handle_help_init(
            {
                "action": "accept",
                "accepted": [
                    {"name": "../evil", "description": "bad"},
                    {"name": "good-feature", "description": "ok"},
                ],
                "help_dir": str(help_dir),
                "project_root": str(tmp_path),
            }
        )
        assert result["success"] is False
        assert "Invalid feature name" in result["error"]
        # The poisoned manifest must not have been written.
        assert not (help_dir / "features.yaml").exists()
