"""Behavioral coverage for the paginated security-audit workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.security_audit import (
    SecurityAuditWorkspaceAdapter,
    SecurityAuditWorkspaceState,
    SecurityFindingReceipt,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    for name in ("a.py", "b.py", "c.py"):
        (repo / "src" / name).write_text("value = 1\n")
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(SecurityAuditWorkspaceAdapter(repo))
    return host


def _payload(render, action: str) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": False,
        **render.record.binding.to_payload(),
    }


def _finding(path: str, severity: str, line: int) -> dict[str, object]:
    return {
        "path": path,
        "line": line,
        "severity": severity,
        "category": "path traversal",
        "detail": f"validate {path}",
        "cwe": "CWE-22",
    }


@pytest.mark.asyncio
async def test_clean_or_medium_scan_finishes_without_confirmation(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("security-audit", {"path": "src", "focus": "full sweep"})
    assert running.record.view.actions == ()
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "scan_result",
            "success": True,
            "health_score": 92,
            "files_scanned": 3,
            "findings": [_finding("src/a.py", "MEDIUM", 1)],
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["finding_count"] == 1
    assert "3" in terminal.render.markdown


@pytest.mark.asyncio
async def test_high_findings_are_paginated_and_handoff_does_not_mutate(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("security-audit", {"path": "src"})
    review = await host.publish(
        running.record.workspace_id,
        {
            "kind": "scan_result",
            "success": True,
            "health_score": 40,
            "files_scanned": 3,
            "findings": [
                _finding("src/c.py", "HIGH", 3),
                _finding("src/a.py", "CRITICAL", 1),
                _finding("src/b.py", "HIGH", 2),
            ],
        },
    )
    assert "finding 1/3" in review.record.view.title.lower()
    assert "src/a.py:1" in review.render.markdown
    first = _payload(review, "next_finding")
    second = await host.collect(first)
    with pytest.raises(CommandWorkspaceError, match="revision|nonce|authority"):
        await host.collect(first)
    assert "finding 2/3" in second.record.view.title.lower()
    third = await host.collect(_payload(second, "next_finding"))
    assert "finding 3/3" in third.record.view.title.lower()
    second_again = await host.collect(_payload(third, "previous_finding"))
    handoff = await host.collect(_payload(second_again, "handoff_to_fix"))
    assert handoff.record.terminal is True
    assert handoff.result["delegate"] == "fix.open"
    assert len(handoff.result["findings"]) == 3
    assert handoff.result["handoff_prepared"] is True
    assert "no remediation executed" in handoff.render.markdown


@pytest.mark.asyncio
async def test_failed_scan_never_renders_clean(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("security-audit", {"path": "src"})
    terminal = await host.publish(
        running.record.workspace_id,
        {"kind": "scan_result", "success": False, "error": "SDK unavailable"},
    )
    assert terminal.result["success"] is False
    assert "did not complete" in terminal.render.markdown
    assert "Health score" not in terminal.render.markdown


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("", 1, "HIGH", "c", "d"), "required"),
        (("x.py", 0, "HIGH", "c", "d"), "positive integer"),
        (("x.py", 1, "INFO", "c", "d"), "severity"),
    ],
)
def test_finding_validation(args: tuple[object, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        SecurityFindingReceipt(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target_path": ""}, "target path"),
        ({"focus": ""}, "focus"),
        ({"stage": "bad"}, "stage"),
        ({"health_score": 101}, "health score"),
        ({"files_scanned": -1}, "must not be negative"),
        ({"stage": "review", "review_index": 0}, "review index"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "error": "bad"}, "cannot carry"),
        ({"handoff_prepared": True}, "requires a successful scan"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"target_path": "src", "focus": "full"}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        SecurityAuditWorkspaceState(**values)


def test_adapter_rejects_paths_actions_and_bad_events(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = SecurityAuditWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"path": "../outside"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"path": "missing"})
    with pytest.raises(CommandWorkspaceError, match="unknown security-audit"):
        adapter.create({"path": "src", "extra": True})
    running = adapter.create({"path": "src"})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"path": "src"}, prior_state=running)
    response = WorkspaceActionResponse(WorkspaceViewId.EXECUTION, "other", False)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.apply(object(), response)
    with pytest.raises(CommandWorkspaceError, match="review stage"):
        adapter.apply(running, response)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.publish(object(), {"kind": "scan_result"})
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(running, {"kind": "scan_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="requires error"):
        adapter.publish(running, {"kind": "scan_result", "success": False})
    with pytest.raises(CommandWorkspaceError, match="health_score"):
        adapter.publish(
            running,
            {"kind": "scan_result", "success": True, "health_score": "good"},
        )
    with pytest.raises(CommandWorkspaceError, match="findings must be a list"):
        adapter.publish(
            running,
            {
                "kind": "scan_result",
                "success": True,
                "health_score": 90,
                "files_scanned": 1,
                "findings": "bad",
            },
        )
    with pytest.raises(CommandWorkspaceError, match="must not be empty"):
        adapter.publish(
            running,
            {
                "kind": "scan_result",
                "success": True,
                "health_score": 90,
                "files_scanned": 1,
                "findings": [_finding("", "HIGH", 1)],
            },
        )
    finding = SecurityFindingReceipt("src/a.py", 1, "HIGH", "c", "d")
    review = replace(running, stage="review", success=True, findings=(finding,))
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(review, response)
