"""Unit tests for the actor-id resolver."""

from __future__ import annotations

import os

import pytest

from attune.bulletin.actor_id import resolve_actor


@pytest.fixture(autouse=True)
def _no_cc_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default to no Claude Code session env so tests are deterministic."""
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)


class TestDefaultCli:
    def test_no_kind_no_env_returns_cli(self) -> None:
        actor_id, kind = resolve_actor()
        assert kind == "cli"
        assert actor_id.startswith("cli-")
        assert str(os.getpid()) in actor_id


class TestClaudeCodeSession:
    def test_cc_env_returns_session_kind(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAUDE_CODE_SESSION_ID",
            "abc123def4567890-rest-of-uuid",
        )
        actor_id, kind = resolve_actor()
        assert kind == "claude-code-session"
        # First 12 chars of the session id
        assert actor_id == "cc-abc123def456"

    def test_cc_env_with_short_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "short")
        actor_id, kind = resolve_actor()
        assert kind == "claude-code-session"
        assert actor_id == "cc-short"


class TestDashboard:
    def test_dashboard_kind_uses_hostname(self) -> None:
        actor_id, kind = resolve_actor(actor_kind="dashboard")
        assert kind == "dashboard"
        assert actor_id.startswith("dashboard-")


class TestScheduled:
    def test_scheduled_uses_task_id(self) -> None:
        actor_id, kind = resolve_actor(actor_kind="scheduled", scheduled_task_id="nightly-rollup")
        assert kind == "scheduled"
        assert actor_id == "sched-nightly-rollup"

    def test_scheduled_without_task_id_defaults(self) -> None:
        actor_id, kind = resolve_actor(actor_kind="scheduled")
        assert kind == "scheduled"
        assert actor_id == "sched-unknown"


class TestMcp:
    def test_mcp_without_cc_env_uses_pid(self) -> None:
        actor_id, kind = resolve_actor(actor_kind="mcp")
        assert kind == "mcp"
        assert actor_id.startswith("mcp-")
        assert str(os.getpid()) in actor_id

    def test_mcp_with_cc_env_inherits_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MCP handler called from a CC session reports the session id."""
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc123def4567890")
        actor_id, kind = resolve_actor(actor_kind="mcp")
        # Kind stays "mcp" so the dashboard can tell who's invoking,
        # but the id ties back to the originating session.
        assert kind == "mcp"
        assert actor_id == "cc-abc123def456"


class TestAttuneRec:
    def test_attune_rec_inherits_dashboard_shape(self) -> None:
        actor_id, kind = resolve_actor(actor_kind="attune-rec")
        assert kind == "attune-rec"
        assert actor_id.startswith("dashboard-")


class TestHostnameSanitization:
    def test_hostname_strips_domain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import attune.bulletin.actor_id as mod

        monkeypatch.setattr(mod.socket, "gethostname", lambda: "patrick-mbp.local")
        actor_id, _ = resolve_actor()
        assert actor_id.startswith("cli-patrick-mbp-")
        assert ".local" not in actor_id

    def test_hostname_unsafe_chars_replaced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import attune.bulletin.actor_id as mod

        monkeypatch.setattr(mod.socket, "gethostname", lambda: "host with spaces")
        actor_id, _ = resolve_actor()
        # spaces become dashes
        assert " " not in actor_id

    def test_hostname_failure_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import attune.bulletin.actor_id as mod

        def _boom() -> str:
            raise OSError("no network")

        monkeypatch.setattr(mod.socket, "gethostname", _boom)
        actor_id, _ = resolve_actor()
        assert "unknown" in actor_id
