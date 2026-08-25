"""Unit tests for collect_subagent_transcripts.

Recovers per-subagent findings from the SDK's session storage
after a multi-subagent workflow run. See
attune-ai 6.2.0 spec: .claude/plans/feature-agent-sdk-0163-uplift-2026-04-19.md
(task #1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest


def _msg(type_: str, content: Any) -> Any:
    """Build a minimal SessionMessage-shaped stand-in.

    Only the fields the helper reads (`type`, `message`) matter.
    """

    @dataclass
    class _M:
        type: str
        message: Any

    return _M(type=type_, message=content)


@pytest.mark.asyncio
async def test_returns_empty_dict_for_none_session_id() -> None:
    from attune.workflows.agent_sdk_adapter import collect_subagent_transcripts

    assert await collect_subagent_transcripts(None) == {}


@pytest.mark.asyncio
async def test_returns_empty_dict_when_sdk_lacks_list_subagents() -> None:
    """Graceful degradation when running against an older SDK."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    with (
        patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", None, create=True),
        patch.object(
            agent_sdk_adapter.claude_agent_sdk,
            "get_subagent_messages",
            None,
            create=True,
        ),
    ):
        # Both attributes present but None; getattr returns None so helper degrades.
        assert await agent_sdk_adapter.collect_subagent_transcripts("sess-1") == {}


@pytest.mark.asyncio
async def test_returns_empty_dict_when_sdk_attrs_missing() -> None:
    """Helper must handle SDKs that don't expose the symbols at all."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    # delattr semantics via patch; `create=True` needed because we're
    # deleting attrs that must never exist during this test.
    sdk = agent_sdk_adapter.claude_agent_sdk
    saved_list = getattr(sdk, "list_subagents", None)
    saved_get = getattr(sdk, "get_subagent_messages", None)
    try:
        if hasattr(sdk, "list_subagents"):
            delattr(sdk, "list_subagents")
        if hasattr(sdk, "get_subagent_messages"):
            delattr(sdk, "get_subagent_messages")
        assert await agent_sdk_adapter.collect_subagent_transcripts("sess-1") == {}
    finally:
        if saved_list is not None:
            sdk.list_subagents = saved_list
        if saved_get is not None:
            sdk.get_subagent_messages = saved_get


@pytest.mark.asyncio
async def test_happy_path_extracts_assistant_text() -> None:
    """Full flow: list two subagents, each with mixed message types."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    messages_by_id = {
        "agent-A": [
            _msg("user", {"content": "start"}),
            _msg(
                "assistant",
                {
                    "content": [
                        {"type": "text", "text": "finding 1"},
                        {"type": "tool_use", "name": "Read", "input": {"path": "a.py"}},
                        {"type": "text", "text": "finding 2"},
                    ]
                },
            ),
            _msg("assistant", {"content": "final remark"}),
        ],
        "agent-B": [
            _msg(
                "assistant",
                {"content": [{"type": "text", "text": "sole finding"}]},
            ),
        ],
    }

    def fake_list(session_id: str, directory: str | None = None) -> list[str]:
        return ["agent-A", "agent-B"]

    def fake_get(session_id: str, agent_id: str, directory: str | None = None, **_) -> list[Any]:
        return messages_by_id[agent_id]

    with (
        patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", fake_list, create=True),
        patch.object(
            agent_sdk_adapter.claude_agent_sdk,
            "get_subagent_messages",
            fake_get,
            create=True,
        ),
    ):
        result = await agent_sdk_adapter.collect_subagent_transcripts("sess-xyz")

    assert set(result) == {"agent-A", "agent-B"}
    assert result["agent-A"] == ["finding 1", "finding 2", "final remark"]
    assert result["agent-B"] == ["sole finding"]


@pytest.mark.asyncio
async def test_individual_subagent_failure_does_not_block_others() -> None:
    """If one agent's get_subagent_messages raises, the others must still surface."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    def fake_list(session_id: str, directory: str | None = None) -> list[str]:
        return ["agent-broken", "agent-ok"]

    def fake_get(session_id: str, agent_id: str, directory: str | None = None, **_) -> list[Any]:
        if agent_id == "agent-broken":
            raise OSError("transcript file missing")
        return [_msg("assistant", {"content": [{"type": "text", "text": "ok"}]})]

    with (
        patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", fake_list, create=True),
        patch.object(
            agent_sdk_adapter.claude_agent_sdk,
            "get_subagent_messages",
            fake_get,
            create=True,
        ),
    ):
        result = await agent_sdk_adapter.collect_subagent_transcripts("sess-partial")

    assert "agent-broken" not in result
    assert result["agent-ok"] == ["ok"]


@pytest.mark.asyncio
async def test_list_subagents_failure_returns_empty() -> None:
    """A failure on the list call degrades to an empty result, not a raise."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    def fake_list(session_id: str, directory: str | None = None) -> list[str]:
        raise FileNotFoundError("sessions dir missing")

    with patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", fake_list, create=True):
        result = await agent_sdk_adapter.collect_subagent_transcripts("sess-missing")

    assert result == {}


@pytest.mark.asyncio
async def test_extracts_plain_string_content() -> None:
    """Some SDK payloads expose `content` as a bare string rather than a block list."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    def fake_list(session_id: str, directory: str | None = None) -> list[str]:
        return ["agent-str"]

    def fake_get(session_id: str, agent_id: str, directory: str | None = None, **_) -> list[Any]:
        return [_msg("assistant", {"content": "direct string content"})]

    with (
        patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", fake_list, create=True),
        patch.object(
            agent_sdk_adapter.claude_agent_sdk,
            "get_subagent_messages",
            fake_get,
            create=True,
        ),
    ):
        result = await agent_sdk_adapter.collect_subagent_transcripts("sess-str")

    assert result["agent-str"] == ["direct string content"]


@pytest.mark.asyncio
async def test_skips_subagents_with_no_assistant_text() -> None:
    """A subagent whose messages are all user/tool-use contributes no key."""
    from attune.models import sdk_adapter as agent_sdk_adapter

    def fake_list(session_id: str, directory: str | None = None) -> list[str]:
        return ["agent-noisy", "agent-empty"]

    def fake_get(session_id: str, agent_id: str, directory: str | None = None, **_) -> list[Any]:
        if agent_id == "agent-empty":
            return [
                _msg("user", {"content": "prompt"}),
                _msg(
                    "assistant",
                    {"content": [{"type": "tool_use", "name": "Read", "input": {}}]},
                ),
            ]
        return [_msg("assistant", {"content": [{"type": "text", "text": "ok"}]})]

    with (
        patch.object(agent_sdk_adapter.claude_agent_sdk, "list_subagents", fake_list, create=True),
        patch.object(
            agent_sdk_adapter.claude_agent_sdk,
            "get_subagent_messages",
            fake_get,
            create=True,
        ),
    ):
        result = await agent_sdk_adapter.collect_subagent_transcripts("sess-mixed")

    assert set(result) == {"agent-noisy"}
    assert "agent-empty" not in result
