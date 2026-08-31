"""Behavioral coverage for the classified memory workspace."""

from __future__ import annotations

from dataclasses import replace

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.memory_context import (
    MemoryContextWorkspaceAdapter,
    MemoryContextWorkspaceState,
)


def _host() -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(MemoryContextWorkspaceAdapter())
    return host


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


@pytest.mark.asyncio
async def test_store_requires_confirmation_and_same_value_retrieval() -> None:
    host = _host()
    preview = await host.open(
        "memory-and-context",
        {
            "operation": "store",
            "key": "renderer-pattern",
            "value": {"rule": "one canonical revision"},
            "classification": "INTERNAL",
            "pattern_type": "architecture",
        },
    )
    assert "one canonical revision" not in preview.markdown
    assert "redacted" in preview.markdown
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "store_memory"))
    running = await host.collect(_payload(preview, "store_memory", confirmed=True))
    assert running.result["delegate"] == "memory_store"
    verifying = await host.publish(
        running.record.workspace_id,
        {
            "kind": "operation_result",
            "success": True,
            "key": "renderer-pattern",
            "classification": "INTERNAL",
        },
    )
    assert verifying.result == {
        "delegate": "memory_retrieve",
        "args": {"key": "renderer-pattern"},
    }
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "verification_result",
            "success": True,
            "data": {
                "value": {"rule": "one canonical revision"},
                "classification": "INTERNAL",
            },
            "source": "short_term",
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["found"] is True
    assert terminal.result["value_digest"]
    assert "one canonical revision" not in terminal.render.markdown


@pytest.mark.asyncio
async def test_forget_requires_confirmation_and_post_delete_miss() -> None:
    host = _host()
    preview = await host.open(
        "memory-and-context",
        {"operation": "forget", "key": "renderer-pattern", "scope": "all"},
    )
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "forget_memory"))
    running = await host.collect(_payload(preview, "forget_memory", confirmed=True))
    assert running.result["args"]["scope"] == "all"
    verifying = await host.publish(
        running.record.workspace_id,
        {
            "kind": "operation_result",
            "success": True,
            "key": "renderer-pattern",
            "removed_from": ["session", "persistent"],
        },
    )
    assert verifying.record.state.stage == "verifying"
    terminal = await host.publish(
        running.record.workspace_id,
        {"kind": "verification_result", "success": True, "data": None},
    )
    assert terminal.record.terminal is True
    assert terminal.result["found"] is False
    assert terminal.result["removed_from"] == ["session", "persistent"]
    assert "post-delete retrieval found no value" in terminal.render.markdown


@pytest.mark.asyncio
async def test_retrieve_search_and_failure_receipts_are_truthful() -> None:
    host = _host()
    retrieve = await host.open("memory-and-context", {"operation": "retrieve", "key": "missing"})
    retrieve = await host.collect(_payload(retrieve, "retrieve_memory"))
    retrieve = await host.publish(
        retrieve.record.workspace_id,
        {"kind": "operation_result", "success": True, "data": None},
    )
    assert retrieve.result["found"] is False

    search = await host.open(
        "memory-and-context",
        {"operation": "search", "query": "renderer", "pattern_type": "architecture"},
    )
    search = await host.collect(_payload(search, "search_memory"))
    search = await host.publish(
        search.record.workspace_id,
        {
            "kind": "operation_result",
            "success": True,
            "results": [{"key": "renderer-pattern"}],
            "count": 1,
        },
    )
    assert search.result["count"] == 1
    assert "1 matches" in search.render.markdown

    failed = await host.open("memory-and-context", {"operation": "retrieve", "key": "x"})
    failed = await host.collect(_payload(failed, "retrieve_memory"))
    failed = await host.publish(
        failed.record.workspace_id,
        {"kind": "operation_result", "success": False, "error": "backend unavailable"},
    )
    assert failed.result["success"] is False
    assert "did not complete" in failed.render.markdown


@pytest.mark.parametrize(
    ("intake", "message"),
    [
        ({}, "operation"),
        ({"operation": "retrieve", "key": ""}, "key or query"),
        ({"operation": "store", "key": "x"}, "non-null value"),
        ({"operation": "store", "key": "x", "value": None}, "non-null value"),
        ({"operation": "store", "key": "x", "value": {1}}, "JSON serializable"),
        (
            {"operation": "store", "key": "x", "value": "v", "classification": "TOP"},
            "classification",
        ),
        ({"operation": "forget", "key": "x", "scope": "world"}, "scope"),
        ({"operation": "retrieve", "key": "x", "extra": True}, "unknown memory"),
    ],
)
def test_intake_validation(intake: dict[str, object], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        MemoryContextWorkspaceAdapter().create(intake)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"stage": "bad"}, "stage"),
        ({"value_json": "bad"}, "value_json"),
        ({"result_count": -1}, "must not be negative"),
        ({"removed_from": ("world",)}, "removed_from"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "error": "bad"}, "cannot carry"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"operation": "retrieve", "key_or_query": "x"}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        MemoryContextWorkspaceState(**values)


def test_adapter_rejects_illegal_receipts_and_verification_mismatches() -> None:
    adapter = MemoryContextWorkspaceAdapter()
    preview = adapter.create({"operation": "store", "key": "x", "value": "v"})
    response = WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "other", False)
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"operation": "retrieve", "key": "x"}, prior_state=preview)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.apply(object(), response)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, response)
    running = replace(preview, stage="running")
    with pytest.raises(CommandWorkspaceError, match="current stage"):
        adapter.publish(running, {"kind": "verification_result"})
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(running, {"kind": "operation_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="requires error"):
        adapter.publish(running, {"kind": "operation_result", "success": False})
    with pytest.raises(CommandWorkspaceError, match="key does not match"):
        adapter.publish(
            running,
            {"kind": "operation_result", "success": True, "key": "other"},
        )
    verifying = replace(preview, stage="verifying")
    mismatch = adapter.publish(
        verifying,
        {
            "kind": "verification_result",
            "success": True,
            "data": {"value": "other", "classification": "PUBLIC"},
        },
    )
    assert mismatch.state.success is False
    assert "did not match" in mismatch.state.error
