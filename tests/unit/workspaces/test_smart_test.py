"""Behavioral coverage for the audited smart-test workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.smart_test import (
    SmartTestWorkspaceAdapter,
    SmartTestWorkspaceState,
    TestGapReceipt,
    WrittenTestReceipt,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "logic.py").write_text("def calculate():\n    return 1\n")
    (repo / "tests").mkdir()
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(SmartTestWorkspaceAdapter(repo))
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


def _audit_event() -> dict[str, object]:
    return {
        "kind": "audit_result",
        "success": True,
        "gaps": [
            {
                "path": "src/logic.py",
                "symbol": "calculate",
                "risk": "HIGH",
                "detail": "no error-path test",
            }
        ],
        "proposed_files": ["tests/test_logic.py"],
    }


@pytest.mark.asyncio
async def test_audit_then_confirmed_generation_hashes_disk_and_runs_probe(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    preview = await host.open("smart-test", {"path": "src/logic.py", "approach": "both"})
    auditing = await host.collect(_payload(preview, "audit_test_gaps"))
    proposal = await host.publish(auditing.record.workspace_id, _audit_event())
    assert r"tests/test\_logic.py" in proposal.render.markdown
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(proposal, "generate_tests"))
    generating = await host.collect(_payload(proposal, "generate_tests", confirmed=True))
    assert generating.result["approved_paths"] == ["tests/test_logic.py"]
    generated = repo / "tests" / "test_logic.py"
    generated.write_text("def test_calculate():\n    assert 1 == 1\n")
    validating = await host.publish(
        generating.record.workspace_id,
        {
            "kind": "generation_result",
            "success": True,
            "written_files": ["tests/test_logic.py"],
        },
    )
    assert validating.result == {"delegate": "tests.run", "paths": ["tests/test_logic.py"]}
    terminal = await host.publish(
        generating.record.workspace_id,
        {
            "kind": "validation_result",
            "probe": "pytest tests/test_logic.py -q",
            "exit_code": 0,
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["written_files"][0]["sha256"]
    assert "validation exited 0" in terminal.render.markdown


@pytest.mark.asyncio
async def test_gap_only_and_stop_after_audit_never_write(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    gap = await host.open("smart-test", {"path": "src", "approach": "gap"})
    gap = await host.collect(_payload(gap, "audit_test_gaps"))
    event = _audit_event()
    event.pop("proposed_files")
    gap = await host.publish(gap.record.workspace_id, event)
    assert gap.record.terminal is True
    assert gap.result["written_files"] == []

    both = await host.open("smart-test", {"path": "src", "approach": "both"})
    both = await host.collect(_payload(both, "audit_test_gaps"))
    no_gaps = await host.publish(
        both.record.workspace_id,
        {"kind": "audit_result", "success": True, "gaps": []},
    )
    assert no_gaps.record.terminal is True
    assert no_gaps.result["success"] is True

    both = await host.open("smart-test", {"path": "src", "approach": "both"})
    both = await host.collect(_payload(both, "audit_test_gaps"))
    both = await host.publish(both.record.workspace_id, _audit_event())
    both = await host.collect(_payload(both, "finish_audit"))
    assert both.record.terminal is True
    assert "no files written" in both.render.markdown


@pytest.mark.asyncio
async def test_generation_and_test_failures_keep_truthful_rollback_receipts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    preview = await host.open("smart-test", {"path": "src", "approach": "generate"})
    auditing = await host.collect(_payload(preview, "audit_test_gaps"))
    proposal = await host.publish(auditing.record.workspace_id, _audit_event())
    generating = await host.collect(_payload(proposal, "generate_tests", confirmed=True))
    failed = await host.publish(
        generating.record.workspace_id,
        {"kind": "generation_result", "success": False, "error": "provider failed"},
    )
    assert "did not complete" in failed.render.markdown

    second = await host.open("smart-test", {"path": "src", "approach": "both"})
    second = await host.collect(_payload(second, "audit_test_gaps"))
    second = await host.publish(second.record.workspace_id, _audit_event())
    second = await host.collect(_payload(second, "generate_tests", confirmed=True))
    (repo / "tests" / "test_logic.py").write_text("def test_bad():\n    assert False\n")
    second = await host.publish(
        second.record.workspace_id,
        {"kind": "generation_result", "success": True, "written_files": ["tests/test_logic.py"]},
    )
    second = await host.publish(
        second.record.workspace_id,
        {"kind": "validation_result", "probe": "pytest", "exit_code": 1},
    )
    assert second.result["success"] is False
    assert second.result["written_files"]
    assert "exited 1" in second.render.markdown


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("", "f", "HIGH", "d"), "required"),
        (("p", "f", "CRITICAL", "d"), "risk"),
    ],
)
def test_gap_validation(args: tuple[str, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        TestGapReceipt(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target_path": ""}, "target_path"),
        ({"approach": "bad"}, "approach"),
        ({"stage": "bad"}, "stage"),
        ({"proposed_files": ("x", "x")}, "proposed files"),
        (
            {"written_files": (WrittenTestReceipt("x", "a"), WrittenTestReceipt("x", "b"))},
            "written files",
        ),
        ({"validation_exit_code": True}, "exit code"),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "error": "bad"}, "cannot carry"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"target_path": "src", "approach": "both"}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        SmartTestWorkspaceState(**values)


def test_adapter_rejects_paths_events_and_unapproved_writes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = SmartTestWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"path": "../outside"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"path": "missing"})
    with pytest.raises(CommandWorkspaceError, match="unknown smart-test"):
        adapter.create({"path": "src", "extra": True})
    preview = adapter.create({"path": "src"})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"path": "src"}, prior_state=preview)
    response = WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "other", False)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.apply(object(), response)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, response)
    auditing = replace(preview, stage="auditing")
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(auditing, {"kind": "audit_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="gaps must be a list"):
        adapter.publish(auditing, {"kind": "audit_result", "success": True, "gaps": "bad"})
    with pytest.raises(CommandWorkspaceError, match="gap must be a mapping"):
        adapter.publish(auditing, {"kind": "audit_result", "success": True, "gaps": [1]})
    missing_proposal = _audit_event()
    missing_proposal.pop("proposed_files")
    with pytest.raises(CommandWorkspaceError, match="proposed file paths"):
        adapter.publish(auditing, missing_proposal)
    proposal = replace(preview, stage="proposal", proposed_files=("tests/test_logic.py",))
    generating = replace(proposal, stage="generating")
    with pytest.raises(CommandWorkspaceError, match="approved paths"):
        adapter.publish(
            generating,
            {"kind": "generation_result", "success": True, "written_files": []},
        )
    with pytest.raises(CommandWorkspaceError, match="current stage"):
        adapter.publish(preview, {"kind": "audit_result"})
