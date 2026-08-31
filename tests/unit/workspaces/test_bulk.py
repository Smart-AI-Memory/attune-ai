"""Behavioral coverage for the asynchronous bulk workspace."""

from __future__ import annotations

from dataclasses import replace

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.bulk import BulkRequest, BulkWorkspaceAdapter, BulkWorkspaceState


def _host() -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(BulkWorkspaceAdapter())
    return host


def _requests() -> list[dict[str, object]]:
    return [
        {
            "task_id": "security-src",
            "task_type": "security_audit",
            "input_data": {"path": "src"},
            "model_tier": "capable",
        },
        {
            "task_id": "docs-src",
            "task_type": "doc_audit",
            "input_data": {"path": "src"},
            "model_tier": "cheap",
        },
    ]


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
async def test_confirmed_submission_records_exact_provider_receipt_and_fallback() -> None:
    host = _host()
    preview = await host.open("bulk", {"requests": _requests()})
    assert "2 non-urgent tasks" in preview.markdown
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "submit_batch"))
    running = await host.collect(_payload(preview, "submit_batch", confirmed=True))
    assert running.result["delegate"] == "bulk.submit"
    assert [item["task_id"] for item in running.result["requests"]] == [
        "security-src",
        "docs-src",
    ]
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "submission_result",
            "success": True,
            "batch_id": "msgbatch_123",
            "accepted_count": 2,
            "status": "submitted",
            "detail": "accepted by provider",
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["batch_id"] == "msgbatch_123"
    assert terminal.result["accepted_count"] == 2
    assert "Submitted 2/2 tasks" in terminal.render.markdown
    assert "msgbatch_123" in terminal.render.html


@pytest.mark.asyncio
async def test_reconnect_is_read_only_and_pending_is_not_called_completed() -> None:
    host = _host()
    preview = await host.open("bulk", {"batch_id": "msgbatch_123"})
    running = await host.collect(_payload(preview, "check_batch"))
    assert running.result == {"delegate": "bulk.status", "batch_id": "msgbatch_123"}
    receipt = await host.publish(
        running.record.workspace_id,
        {
            "kind": "status_result",
            "success": True,
            "batch_id": "msgbatch_123",
            "accepted_count": 2,
            "status": "pending",
        },
    )
    assert receipt.record.terminal is True
    assert "is pending" in receipt.render.markdown
    assert "completed" not in receipt.render.markdown.lower()


@pytest.mark.asyncio
async def test_rejection_and_timeout_never_render_submitted() -> None:
    host = _host()
    preview = await host.open("bulk", {"requests": _requests()})
    running = await host.collect(_payload(preview, "submit_batch", confirmed=True))
    failed = await host.publish(
        running.record.workspace_id,
        {
            "kind": "submission_result",
            "success": False,
            "accepted_count": 0,
            "status": "failed",
            "error": "provider timeout",
        },
    )
    assert failed.result["success"] is False
    assert "did not submit" in failed.render.markdown
    assert "Submitted 0/2" not in failed.render.markdown

    reconnect = await host.open("bulk", {"batch_id": "msgbatch_failed"})
    reconnect = await host.collect(_payload(reconnect, "check_batch"))
    reconnect = await host.publish(
        reconnect.record.workspace_id,
        {
            "kind": "status_result",
            "success": False,
            "error": "provider unavailable",
        },
    )
    assert reconnect.result["status"] == "failed"


@pytest.mark.parametrize(
    ("intake", "message"),
    [
        ({}, "non-empty list"),
        ({"requests": []}, "1 to 100"),
        ({"requests": [1]}, "mapping"),
        ({"batch_id": "x", "requests": _requests()}, "not both"),
        ({"extra": True}, "unknown bulk"),
        (
            {"requests": [{"task_id": "x", "task_type": "t", "input_data": []}]},
            "input_data",
        ),
        (
            {
                "requests": [
                    {"task_id": "x", "task_type": "t", "input_data": {}},
                    {"task_id": "x", "task_type": "t", "input_data": {}},
                ]
            },
            "unique",
        ),
    ],
)
def test_intake_validation(intake: dict[str, object], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        BulkWorkspaceAdapter().create(intake)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"mode": "bad"}, "mode"),
        ({"stage": "bad"}, "stage"),
        ({"accepted_count": -1}, "accepted_count"),
        ({"provider_status": "unknown"}, "provider status"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "error": "bad"}, "cannot carry"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "mode": "submit",
        "requests": (BulkRequest("x", "t", "{}"),),
    }
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        BulkWorkspaceState(**values)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("", "t", "{}"), "task_id"),
        (("x", "", "{}"), "task_type"),
        (("x", "t", "{}", "unknown"), "model_tier"),
        (("x", "t", "not-json"), "JSON object"),
        (("x", "t", "[]"), "JSON object"),
    ],
)
def test_request_validation(args: tuple[str, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        BulkRequest(*args)


def test_additional_state_and_json_validation() -> None:
    with pytest.raises(CommandWorkspaceError, match="submission requires"):
        BulkWorkspaceState(mode="submit")
    with pytest.raises(CommandWorkspaceError, match="reconnect requires"):
        BulkWorkspaceState(mode="resume")
    with pytest.raises(CommandWorkspaceError, match="JSON serializable"):
        BulkWorkspaceAdapter().create(
            {"requests": [{"task_id": "x", "task_type": "t", "input_data": {"bad": {1}}}]}
        )


def test_adapter_rejects_illegal_actions_events_and_receipts() -> None:
    adapter = BulkWorkspaceAdapter()
    preview = adapter.create({"requests": _requests()})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"requests": _requests()}, prior_state=preview)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.apply(
            object(),
            WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "other", False),
        )
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(
            preview,
            WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "other", False),
        )
    running = replace(preview, stage="running")
    with pytest.raises(CommandWorkspaceError, match="preview stage"):
        adapter.apply(
            running,
            WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "submit_batch", True),
        )
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.publish(object(), {"kind": "submission_result"})
    with pytest.raises(CommandWorkspaceError, match="running stage"):
        adapter.publish(preview, {"kind": "submission_result"})
    with pytest.raises(CommandWorkspaceError, match="requires submission_result"):
        adapter.publish(running, {"kind": "status_result"})
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(running, {"kind": "submission_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="status is invalid"):
        adapter.publish(
            running,
            {"kind": "submission_result", "success": False, "status": "unknown"},
        )
    with pytest.raises(CommandWorkspaceError, match="non-negative integer"):
        adapter.publish(
            running,
            {"kind": "submission_result", "success": False, "accepted_count": True},
        )
    with pytest.raises(CommandWorkspaceError, match="exceeds"):
        adapter.publish(
            running,
            {"kind": "submission_result", "success": False, "accepted_count": 3},
        )
    with pytest.raises(CommandWorkspaceError, match="requires batch_id"):
        adapter.publish(
            running,
            {"kind": "submission_result", "success": True, "accepted_count": 2},
        )
    with pytest.raises(CommandWorkspaceError, match="accept every task"):
        adapter.publish(
            running,
            {
                "kind": "submission_result",
                "success": True,
                "batch_id": "b",
                "accepted_count": 1,
            },
        )
    with pytest.raises(CommandWorkspaceError, match="requires error"):
        adapter.publish(
            running,
            {"kind": "submission_result", "success": False, "status": "failed"},
        )
    resume = adapter.create({"batch_id": "batch"})
    resume = adapter.apply(
        resume,
        WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "check_batch", False),
    ).state
    with pytest.raises(CommandWorkspaceError, match="requires accepted_count"):
        adapter.publish(
            resume,
            {"kind": "status_result", "success": True, "status": "pending"},
        )
