"""MCP handoff adapters voice their own verbs (voice_summary).

Regression guard for the 11.0.0 canary finding (2026-07-28): both
handoff tools answered with the generic recall greeting "Here's what
I found." because the shared voice layer stamps GREETING_SUCCESS over
any response that carries no summary of its own — the same class of
bug fixed for the session_memory_* adapters in #1684.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.handoff import packet as packet_mod
from attune.mcp.handoff_handlers import HandoffHandlersMixin
from attune.voice.personality import GREETING_SUCCESS


class _Server(HandoffHandlersMixin):
    """Minimal host for the mixin — just the workspace root."""

    def __init__(self, root: Path) -> None:
        self._workspace_root = str(root)


class TestHandoffCreateVoice:
    @pytest.mark.asyncio
    async def test_create_voices_the_slug(self, repo: Path) -> None:
        result = await _Server(repo)._handle_handoff_create({"goal": "Ship it"})
        assert result["ok"] is True
        assert result["voice_summary"] == "Wrote the handoff packet for feature-x."

    @pytest.mark.asyncio
    async def test_create_failure_voices_the_reason(self, repo: Path) -> None:
        over_cap = "x" * (packet_mod.FIELD_CAP_BYTES + 1)
        result = await _Server(repo)._handle_handoff_create({"goal": over_cap})
        assert result["ok"] is False
        assert result["voice_summary"] == "Couldn't write the handoff packet (field_over_cap)."


class TestHandoffResumeVoice:
    @pytest.mark.asyncio
    async def test_resume_voices_warnings_and_memory(self, repo: Path) -> None:
        server = _Server(repo)
        await server._handle_handoff_create({"goal": "Ship it"})
        result = await server._handle_handoff_resume({})
        assert result["ok"] is True
        assert result["warnings"] == []
        assert result["voice_summary"] == (
            "Verified the feature-x handoff packet — 0 warnings, memory skipped."
        )

    @pytest.mark.asyncio
    async def test_resume_singular_warning_phrasing(self, repo: Path) -> None:
        server = _Server(repo)
        await server._handle_handoff_create({"goal": "Ship it"})
        # One drift warning: an uncommitted file → dirty_tree.
        (repo / "scratch.txt").write_text("wip\n", encoding="utf-8")
        result = await server._handle_handoff_resume({})
        assert result["ok"] is True
        assert [w["code"] for w in result["warnings"]] == ["dirty_tree"]
        assert result["voice_summary"] == (
            "Verified the feature-x handoff packet — 1 warning, memory skipped."
        )

    @pytest.mark.asyncio
    async def test_resume_missing_packet_voices_the_reason(self, repo: Path) -> None:
        result = await _Server(repo)._handle_handoff_resume({})
        assert result["ok"] is False
        assert result["voice_summary"] == "Couldn't resume the handoff (packet_not_found)."


class TestNoGenericGreeting:
    """The canary assertion: neither handoff verb ever says
    "Here's what I found." on its own — that greeting only fits recall."""

    @pytest.mark.asyncio
    async def test_no_handoff_verb_uses_the_generic_recall_greeting(self, repo: Path) -> None:
        server = _Server(repo)
        create = await server._handle_handoff_create({"goal": "Ship it"})
        resume = await server._handle_handoff_resume({})
        create_fail = await server._handle_handoff_create(
            {"goal": "x" * (packet_mod.FIELD_CAP_BYTES + 1)}
        )
        resume_fail = await server._handle_handoff_resume({"slug": "../evil"})
        for result in (create, resume, create_fail, resume_fail):
            assert result["voice_summary"]
            assert result["voice_summary"] != GREETING_SUCCESS
