"""Behavioral coverage for the claim-verification workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.verify import (
    VerificationFinding,
    VerifyWorkspaceAdapter,
    VerifyWorkspaceState,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "generated.md").write_text("# Generated\n")
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(VerifyWorkspaceAdapter(repo))
    return host


def _deterministic(findings: list[dict[str, object]], *, ok: bool) -> dict[str, object]:
    return {
        "kind": "deterministic_result",
        "success": True,
        "ok": ok,
        "checked": ["imports", "flags", "links", "counts"],
        "findings": findings,
    }


def _error_finding() -> dict[str, object]:
    return {
        "kind": "dead_link",
        "severity": "error",
        "detail": "target does not exist",
        "evidence": "docs/missing.md is absent",
        "location": "generated.md:4",
    }


@pytest.mark.asyncio
async def test_two_layers_complete_with_full_evidence_and_no_actions(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("verify", {"path": "generated.md"})
    assert running.record.view.actions == ()
    cross = await host.publish(running.record.workspace_id, _deterministic([], ok=True))
    assert cross.result == {"delegate": "verify.ambient_cross_check", "path": "generated.md"}
    terminal = await host.publish(
        running.record.workspace_id,
        {
            "kind": "cross_check_result",
            "success": True,
            "findings": [
                {
                    "detail": "security caveat may need a human read",
                    "evidence": "source uses a guarded path",
                    "location": "generated.md:8",
                }
            ],
        },
    )
    assert terminal.record.terminal is True
    assert terminal.result["deterministic_ok"] is True
    assert terminal.result["hard_gate_passed"] is None
    assert terminal.result["findings"][0]["layer"] == "cross_check"
    assert "source uses a guarded path" in terminal.render.markdown


@pytest.mark.asyncio
async def test_deterministic_error_fails_hard_gate_and_warning_does_not(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("verify", {"path": "generated.md", "hard_gate": True})
    cross = await host.publish(
        running.record.workspace_id,
        _deterministic(
            [
                _error_finding(),
                {
                    "kind": "unknown_flag",
                    "severity": "warning",
                    "detail": "command was not allow-listed",
                    "evidence": "--help not captured",
                    "location": "generated.md:6",
                },
            ],
            ok=False,
        ),
    )
    terminal = await host.publish(
        cross.record.workspace_id,
        {"kind": "cross_check_result", "success": True, "findings": []},
    )
    assert terminal.result["hard_gate_passed"] is False
    assert terminal.result["findings"][0]["evidence"] == "docs/missing.md is absent"
    assert "hard gate failed" in terminal.render.markdown


@pytest.mark.asyncio
async def test_checker_and_cross_check_failures_never_render_clean(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    running = await host.open("verify", {"path": "generated.md", "hard_gate": True})
    failed = await host.publish(
        running.record.workspace_id,
        {"kind": "deterministic_result", "success": False, "error": "checker crashed"},
    )
    assert failed.result["completed"] is False
    assert failed.result["hard_gate_passed"] is False
    assert "did not complete" in failed.render.markdown

    second = await host.open("verify", {"path": "generated.md"})
    second = await host.publish(second.record.workspace_id, _deterministic([], ok=True))
    second = await host.publish(
        second.record.workspace_id,
        {"kind": "cross_check_result", "success": False, "error": "context truncated"},
    )
    assert second.result["completed"] is False
    assert "did not complete" in second.render.markdown


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("other", "dead_link", "error", "d", "e", "l"), "layer"),
        (("deterministic", "made_up", "error", "d", "e", "l"), "kind"),
        (("cross_check", "other", "warning", "d", "e", "l"), "kind"),
        (("deterministic", "dead_link", "info", "d", "e", "l"), "severity"),
        (("cross_check", "semantic_cross_check", "error", "d", "e", "l"), "remain warnings"),
        (("deterministic", "dead_link", "error", "", "e", "l"), "required"),
    ],
)
def test_finding_validation(args: tuple[str, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        VerificationFinding(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target_path": ""}, "target_path"),
        ({"hard_gate": "yes"}, "hard_gate"),
        ({"stage": "bad"}, "stage"),
        ({"checked": ("imports", "")}, "checked categories"),
        (
            {
                "deterministic_findings": (
                    VerificationFinding(
                        "cross_check", "semantic_cross_check", "warning", "d", "e", "l"
                    ),
                )
            },
            "deterministic finding layer",
        ),
        ({"completed": True}, "deterministic outcome"),
        ({"completed": True, "deterministic_ok": True, "error": "bad"}, "cannot be marked"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"target_path": "generated.md", "hard_gate": False}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        VerifyWorkspaceState(**values)


def test_adapter_rejects_paths_actions_and_inconsistent_results(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = VerifyWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"path": "../outside.md"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"path": "missing.md"})
    with pytest.raises(CommandWorkspaceError, match="hard_gate must be boolean"):
        adapter.create({"path": "generated.md", "hard_gate": "yes"})
    with pytest.raises(CommandWorkspaceError, match="unknown verify"):
        adapter.create({"path": "generated.md", "extra": True})
    running = adapter.create({"path": "generated.md"})
    with pytest.raises(CommandWorkspaceError, match="cannot be replaced"):
        adapter.create({"path": "generated.md"}, prior_state=running)
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.project(object())
    with pytest.raises(CommandWorkspaceError, match="no actions"):
        adapter.apply(running, object())
    with pytest.raises(CommandWorkspaceError, match="incompatible"):
        adapter.publish(object(), {"kind": "deterministic_result"})
    with pytest.raises(CommandWorkspaceError, match="success must be boolean"):
        adapter.publish(running, {"kind": "deterministic_result", "success": "yes"})
    with pytest.raises(CommandWorkspaceError, match="requires error"):
        adapter.publish(running, {"kind": "deterministic_result", "success": False})
    with pytest.raises(CommandWorkspaceError, match="disagrees"):
        adapter.publish(running, _deterministic([_error_finding()], ok=True))
    cross = replace(running, stage="cross_check", deterministic_ok=True)
    with pytest.raises(CommandWorkspaceError, match="findings must be a list"):
        adapter.publish(
            cross,
            {"kind": "cross_check_result", "success": True, "findings": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="current stage"):
        adapter.publish(running, {"kind": "cross_check_result"})
