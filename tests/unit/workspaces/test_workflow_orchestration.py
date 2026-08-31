"""Behavioral coverage for the multi-workflow orchestration workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.workflow_orchestration import (
    ChildWorkflowReceipt,
    WorkflowOrchestrationAdapter,
    WorkflowOrchestrationState,
)


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(WorkflowOrchestrationAdapter(repo))
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


def _child(name: str, status: str = "PASS") -> dict[str, object]:
    return {
        "kind": "child_result",
        "receipt": {
            "name": name,
            "status": status,
            "detail": f"{name} {status.lower()}",
            "probe": f"probe-{name}",
        },
    }


@pytest.mark.asyncio
async def test_stable_order_progress_and_clean_terminal(tmp_path: Path) -> None:
    host = _host(tmp_path)
    preview = await host.open(
        "workflow-orchestration",
        {
            "goal": "pre-merge confidence",
            "path": ".",
            "workflows": ["security", "tests", "docs"],
        },
    )
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "run_workflows"))
    running = await host.collect(_payload(preview, "run_workflows", confirmed=True))
    assert [child["name"] for child in running.result["children"]] == [
        "security",
        "tests",
        "docs",
    ]
    first_revision = running.record.revision
    for name in ["docs", "security", "tests"]:
        running = await host.publish(running.record.workspace_id, _child(name))
        assert running.record.revision == first_revision
    terminal = await host.publish(
        running.record.workspace_id,
        {"kind": "orchestration_complete"},
    )
    assert terminal.record.terminal is True
    assert list(terminal.result["statuses"]) == ["security", "tests", "docs"]
    assert terminal.result["success"] is True
    assert terminal.render.markdown.index("security") < terminal.render.markdown.index("tests")


@pytest.mark.asyncio
async def test_warning_is_degraded_but_missing_and_error_fail_closed(tmp_path: Path) -> None:
    host = _host(tmp_path)
    warning = await host.open(
        "workflow-orchestration",
        {"goal": "check", "path": ".", "workflows": ["tests", "docs"]},
    )
    warning = await host.collect(_payload(warning, "run_workflows", confirmed=True))
    warning = await host.publish(warning.record.workspace_id, _child("tests"))
    warning = await host.publish(warning.record.workspace_id, _child("docs", "WARNING"))
    warning = await host.publish(
        warning.record.workspace_id,
        {"kind": "orchestration_complete"},
    )
    assert warning.result["success"] is True
    assert warning.result["degraded"] is True
    assert "degraded" in warning.render.markdown

    missing = await host.open(
        "workflow-orchestration",
        {"goal": "check", "path": ".", "workflows": ["security", "tests", "docs"]},
    )
    missing = await host.collect(_payload(missing, "run_workflows", confirmed=True))
    missing = await host.publish(missing.record.workspace_id, _child("security", "ERROR"))
    missing = await host.publish(missing.record.workspace_id, _child("tests"))
    missing = await host.publish(
        missing.record.workspace_id,
        {"kind": "orchestration_complete"},
    )
    assert missing.result["success"] is False
    assert missing.result["statuses"] == {
        "security": "ERROR",
        "tests": "PASS",
        "docs": "MISSING",
    }
    assert missing.result["blockers"] == ["security", "docs"]
    assert "did not complete cleanly" in missing.render.markdown


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("unknown", "PASS", "d", "p"), "name"),
        (("security", "OK", "d", "p"), "status"),
        (("security", "PASS", "", "p"), "required"),
    ],
)
def test_child_receipt_validation(args: tuple[str, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        ChildWorkflowReceipt(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"goal": ""}, "goal"),
        ({"target_path": ""}, "target_path"),
        ({"stage": "bad"}, "stage"),
        ({"workflows": ("security",)}, "2 to 7"),
        ({"workflows": ("security", "security")}, "unique"),
        ({"workflows": ("security", "unknown")}, "workflow is invalid"),
        (
            {
                "receipts": (
                    ChildWorkflowReceipt("security", "PASS", "d", "p"),
                    ChildWorkflowReceipt("security", "PASS", "d", "p"),
                )
            },
            "receipts must be unique",
        ),
        (
            {"receipts": (ChildWorkflowReceipt("docs", "PASS", "d", "p"),)},
            "was not requested",
        ),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "goal": "check",
        "target_path": ".",
        "workflows": ("security", "tests"),
    }
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        WorkflowOrchestrationState(**values)


def test_adapter_rejects_bad_intake_actions_and_child_events(tmp_path: Path) -> None:
    adapter = WorkflowOrchestrationAdapter(tmp_path)
    with pytest.raises(CommandWorkspaceError, match="workflows must be a list"):
        adapter.create({"goal": "x", "workflows": "security"})
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"goal": "x", "path": "../outside", "workflows": ["security", "tests"]})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"goal": "x", "path": "missing", "workflows": ["security", "tests"]})
    with pytest.raises(CommandWorkspaceError, match="unknown orchestration"):
        adapter.create({"goal": "x", "workflows": [], "extra": True})
    preview = adapter.create({"goal": "x", "workflows": ["security", "tests"]})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"goal": "x", "workflows": []}, prior_state=preview)
    response = WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "other", False)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.apply(object(), response)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, response)
    running = replace(preview, stage="running")
    with pytest.raises(CommandWorkspaceError, match="receipt mapping"):
        adapter.publish(running, {"kind": "child_result", "receipt": "bad"})
    with pytest.raises(CommandWorkspaceError, match="not requested"):
        adapter.publish(running, _child("docs"))
    first = adapter.publish(running, _child("security")).state
    with pytest.raises(CommandWorkspaceError, match="already exists"):
        adapter.publish(first, _child("security"))
    with pytest.raises(CommandWorkspaceError, match="Unknown orchestration"):
        adapter.publish(running, {"kind": "other"})
    with pytest.raises(CommandWorkspaceError, match="running stage"):
        adapter.publish(preview, {"kind": "orchestration_complete"})
