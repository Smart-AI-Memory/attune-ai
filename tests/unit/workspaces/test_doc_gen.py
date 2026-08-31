"""Behavioral coverage for the previewed documentation workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.doc_gen import (
    DocGenWorkspaceAdapter,
    DocGenWorkspaceState,
    DocumentationFileReceipt,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "api.py").write_text("def public_api():\n    return 1\n")
    (repo / "docs").mkdir()
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(DocGenWorkspaceAdapter(repo))
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
        "gaps": ["public_api is missing from the API reference"],
        "proposed_files": ["docs/api.md"],
    }


@pytest.mark.asyncio
async def test_preview_confirm_hash_and_reality_probe(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    current = await host.open("doc-gen", {"path": "src/api.py"})
    current = await host.collect(_payload(current, "audit_docs"))
    current = await host.publish(current.record.workspace_id, _audit_event())
    assert "docs/api.md" in current.render.markdown
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(current, "apply_docs"))
    current = await host.collect(_payload(current, "apply_docs", confirmed=True))
    (repo / "docs" / "api.md").write_text("# API\n\n`public_api`\n")
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "generation_result", "success": True, "changed_files": ["docs/api.md"]},
    )
    assert current.result == {"delegate": "doc-import-audit", "paths": ["docs/api.md"]}
    current = await host.publish(
        current.record.workspace_id,
        {
            "kind": "validation_result",
            "success": True,
            "probe": "python scripts/doc_import_audit.py docs/api.md",
        },
    )
    assert current.record.terminal is True
    assert current.result["changed_files"][0]["sha256"]
    assert "validation passed" in current.render.markdown


@pytest.mark.asyncio
async def test_no_gap_and_finish_audit_paths_are_non_mutating(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    no_gap = await host.open("doc-gen", {"path": "src"})
    no_gap = await host.collect(_payload(no_gap, "audit_docs"))
    no_gap = await host.publish(
        no_gap.record.workspace_id,
        {"kind": "audit_result", "success": True, "gaps": [], "proposed_files": []},
    )
    assert no_gap.record.terminal is True
    assert no_gap.result["changed_files"] == []

    proposal = await host.open("doc-gen", {"path": "src"})
    proposal = await host.collect(_payload(proposal, "audit_docs"))
    proposal = await host.publish(proposal.record.workspace_id, _audit_event())
    proposal = await host.collect(_payload(proposal, "finish_doc_audit"))
    assert "no files changed" in proposal.render.markdown


@pytest.mark.asyncio
async def test_generation_or_reality_failure_keeps_changed_hashes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    host = _host(repo)
    current = await host.open("doc-gen", {"path": "src"})
    current = await host.collect(_payload(current, "audit_docs"))
    current = await host.publish(current.record.workspace_id, _audit_event())
    current = await host.collect(_payload(current, "apply_docs", confirmed=True))
    failed = await host.publish(
        current.record.workspace_id,
        {"kind": "generation_result", "success": False, "error": "provider failed"},
    )
    assert "did not complete" in failed.render.markdown

    current = await host.open("doc-gen", {"path": "src"})
    current = await host.collect(_payload(current, "audit_docs"))
    current = await host.publish(current.record.workspace_id, _audit_event())
    current = await host.collect(_payload(current, "apply_docs", confirmed=True))
    (repo / "docs" / "api.md").write_text("fictional_symbol\n")
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "generation_result", "success": True, "changed_files": ["docs/api.md"]},
    )
    current = await host.publish(
        current.record.workspace_id,
        {
            "kind": "validation_result",
            "success": False,
            "probe": "doc-import-audit",
            "error": "fictional symbol",
        },
    )
    assert current.result["success"] is False
    assert current.result["changed_files"]
    assert "fictional symbol" in current.render.markdown


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"target_path": ""}, "target_path"),
        ({"stage": "bad"}, "stage"),
        ({"gaps": ("",)}, "gaps"),
        ({"proposed_files": ("x", "x")}, "proposed files"),
        (
            {
                "changed_files": (
                    DocumentationFileReceipt("x", "a"),
                    DocumentationFileReceipt("x", "b"),
                )
            },
            "changed files",
        ),
        ({"success": False, "error": ""}, "error receipt"),
        ({"success": True, "error": "bad"}, "cannot carry"),
    ],
)
def test_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"target_path": "src"}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        DocGenWorkspaceState(**values)


def test_adapter_rejects_bad_paths_actions_and_receipts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = DocGenWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="escapes"):
        adapter.create({"path": "../outside"})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"path": "missing"})
    with pytest.raises(CommandWorkspaceError, match="unknown doc-gen"):
        adapter.create({"path": "src", "extra": True})
    with pytest.raises(CommandWorkspaceError, match="unknown doc-gen"):
        adapter.create({"path": "src", "doc_type": "api"})
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
    with pytest.raises(CommandWorkspaceError, match="current stage"):
        adapter.publish(preview, {"kind": "audit_result"})
