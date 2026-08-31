"""Behavioral coverage for the read-only bug-predict workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.mcp.server import AttuneMCPServer
from attune.workspaces.bug_predict import (
    BugFindingReceipt,
    BugPredictWorkspaceAdapter,
    BugPredictWorkspaceState,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "risky.py").write_text("# TODO\n")
    (repo / ".git").mkdir()
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(BugPredictWorkspaceAdapter(repo))
    return host


def _findings() -> list[dict[str, object]]:
    return [
        {
            "path": "src/risky.py",
            "line": 8,
            "pattern": "incomplete_code",
            "severity": "LOW",
            "description": "TODO remains",
        },
        {
            "path": "src/risky.py",
            "line": 2,
            "pattern": "dangerous_eval",
            "severity": "HIGH",
            "description": "dynamic execution",
        },
    ]


@pytest.mark.asyncio
async def test_opens_running_without_confirmation_and_completes_read_only(
    tmp_path: Path,
) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open(
        "bug-predict",
        {"path": "src", "severity_filter": "all"},
    )
    assert running.record.view.actions == ()
    assert running.record.action_nonce == ""
    progress = await host.publish(
        running.record.workspace_id,
        {"kind": "progress", "detail": "correlating hotspots"},
    )
    assert progress.record.revision == running.record.revision
    assert progress.record.event_sequence == 1
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "scan_result",
            "success": True,
            "risk_score": 72,
            "findings": _findings(),
            "suggestions": ["Remove dynamic execution", "Add regression tests"],
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result == {
        "success": True,
        "finding_count": 2,
        "risk_score": 72,
        "error": "",
    }
    assert terminal.render.markdown.index("HIGH") < terminal.render.markdown.index("LOW")
    assert "src/risky.py:2" in terminal.render.markdown


@pytest.mark.asyncio
async def test_high_filter_and_failure_receipt_never_render_false_clean(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    running = await host.open(
        "bug-predict",
        {"path": "src", "severity_filter": "high"},
    )
    filtered = await host.publish(
        running.record.workspace_id,
        {
            "kind": "scan_result",
            "success": True,
            "risk_score": 55,
            "findings": _findings(),
            "suggestions": [],
        },
    )
    assert len(filtered.record.state.findings) == 1
    assert "dangerous\\_eval" in filtered.render.markdown
    assert "incomplete\\_code" not in filtered.render.markdown

    failed_running = await host.open("bug-predict", {"path": "src"})
    failed = await host.publish(
        failed_running.record.workspace_id,
        {
            "kind": "scan_result",
            "success": False,
            "risk_score": None,
            "findings": [],
            "suggestions": [],
            "error": "SDK timed out",
        },
    )
    assert failed.record.terminal is True
    assert "did not complete" in failed.render.markdown
    assert "SDK timed out" in failed.render.markdown
    assert "0 findings" not in failed.render.markdown


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("", 1, "p", "HIGH", "d"), "path"),
        (("x.py", 0, "p", "HIGH", "d"), "positive integer"),
        (("x.py", 1, "", "HIGH", "d"), "pattern"),
        (("x.py", 1, "p", "CRITICAL", "d"), "severity"),
        (("x.py", 1, "p", "HIGH", ""), "description"),
    ],
)
def test_finding_validation(args: tuple[object, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        BugFindingReceipt(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target_path": ""}, "target_path"),
        ({"severity_filter": "medium"}, "severity_filter"),
        ({"stage": "preview"}, "stage"),
        ({"stage": "receipt", "success": None}, "requires a success result"),
        ({"risk_score": True}, "risk_score"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "risk_score": None}, "requires a risk_score"),
        ({"success": True, "risk_score": 1, "error": "bad"}, "cannot carry an error"),
        ({"suggestions": ("",)}, "suggestions"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"target_path": "src", "severity_filter": "all"}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        BugPredictWorkspaceState(**values)


def test_adapter_input_event_and_action_validation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = BugPredictWorkspaceAdapter(repo)
    running = adapter.create({"path": "src"})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"path": "src"}, prior_state=running)
    with pytest.raises(CommandWorkspaceError, match="unknown bug-predict intake"):
        adapter.create({"path": "src", "extra": True})
    with pytest.raises(CommandWorkspaceError, match="path must be a string"):
        adapter.create({"path": None})
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"path": "../outside"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"path": "missing"})
    with pytest.raises(CommandWorkspaceError, match="incompatible state"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="no confirmation actions"):
        adapter.apply(running, object())
    with pytest.raises(CommandWorkspaceError, match="incompatible state"):
        adapter.publish(object(), {"kind": "x"})
    with pytest.raises(CommandWorkspaceError, match="detail is required"):
        adapter.publish(running, {"kind": "progress", "detail": ""})
    for success in (None, "yes"):
        with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
            adapter.publish(running, {"kind": "scan_result", "success": success})
    with pytest.raises(CommandWorkspaceError, match="findings must be a list"):
        adapter.publish(
            running,
            {"kind": "scan_result", "success": True, "findings": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="finding must be a mapping"):
        adapter.publish(
            running,
            {"kind": "scan_result", "success": True, "findings": [1]},
        )
    with pytest.raises(CommandWorkspaceError, match="path"):
        adapter.publish(
            running,
            {
                "kind": "scan_result",
                "success": True,
                "risk_score": 1,
                "findings": [
                    {
                        "path": None,
                        "line": 1,
                        "pattern": "edge",
                        "severity": "HIGH",
                        "description": "detail",
                    }
                ],
            },
        )
    with pytest.raises(CommandWorkspaceError, match="suggestions must be a list"):
        adapter.publish(
            running,
            {
                "kind": "scan_result",
                "success": True,
                "findings": [],
                "suggestions": "bad",
            },
        )
    with pytest.raises(CommandWorkspaceError, match="suggestion must be text"):
        adapter.publish(
            running,
            {
                "kind": "scan_result",
                "success": True,
                "risk_score": 1,
                "findings": [],
                "suggestions": [None],
            },
        )
    with pytest.raises(CommandWorkspaceError, match="unknown bug-predict event"):
        adapter.publish(running, {"kind": "missing"})
    terminal = replace(running, stage="receipt", success=False, error="failed")
    with pytest.raises(CommandWorkspaceError, match="terminal bug prediction"):
        adapter.publish(terminal, {"kind": "progress", "detail": "x"})


@pytest.mark.asyncio
async def test_generic_server_registers_both_cohort_adapters(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with (
        patch.object(AttuneMCPServer, "_register_plugin_tools"),
        patch("attune.mcp.version_check.check_for_updates", return_value=None),
    ):
        server = AttuneMCPServer(workspace_root=str(repo))
    release = await server.call_tool(
        "command_workspace_open",
        {
            "adapter_id": "release-prep",
            "intake": {"version": "1.0.0", "scope": "full", "project_path": "."},
        },
    )
    bug = await server.call_tool(
        "command_workspace_open",
        {"adapter_id": "bug-predict", "intake": {"path": "src"}},
    )
    assert release["success"] is True
    assert bug["success"] is True
    assert bug["action_nonce"] == ""
