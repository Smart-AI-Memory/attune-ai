"""Behavioral coverage for the shared command-workspace host."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceHost,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)
from attune.elicitation.fix_workspace import FixWorkspaceState
from attune.mcp.server import AttuneMCPServer


@dataclass(frozen=True)
class _State:
    stage: str


class _Adapter:
    adapter_id = "example"
    schema_version = 1

    def __init__(self) -> None:
        self.project_suffix = ""
        self.contract_suffix = ""
        self.receipt_actions = False

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> _State:
        if prior_state is not None and prior_state != _State("intake"):
            raise CommandWorkspaceError(["select edit before replacing preview"])
        return _State(str(intake.get("stage", "preview")))

    def project(self, state: object) -> CommandWorkspaceProjection:
        if not isinstance(state, _State):
            raise CommandWorkspaceError(["incompatible example state"])
        if state.stage == "preview":
            data = {
                "id": "preview",
                "title": f"Example workspace{self.project_suffix}",
                "actions": [
                    {"id": "edit", "label": "Edit"},
                    {
                        "id": "approve",
                        "label": "Approve",
                        "consequence": "Approve this exact example.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        elif state.stage == "intake":
            data = {
                "id": "intake",
                "title": "Example intake",
                "summary": "Submit replacement intake.",
            }
        else:
            data = {
                "id": "receipt",
                "title": "Example receipt",
                "summary": "The example completed.",
            }
            if self.receipt_actions:
                data["actions"] = [{"id": "again", "label": "Again"}]
        view = workspace_from_dict(data)
        material = f"{state.stage}:{view!r}:{self.contract_suffix}".encode()
        return CommandWorkspaceProjection(
            view,
            hashlib.sha256(material).hexdigest(),
        )

    def apply(
        self,
        state: object,
        action: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        if state != _State("preview"):
            raise CommandWorkspaceError(["example is not awaiting an action"])
        if action.action == "edit":
            return CommandWorkspaceTransition(_State("intake"))
        if action.action == "approve":
            return CommandWorkspaceTransition(
                _State("receipt"),
                terminal=True,
                result={"approved_value": "example"},
            )
        raise CommandWorkspaceError(["unsupported example action"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        kind = event.get("kind")
        if kind == "progress":
            return CommandWorkspaceTransition(
                state,
                result={"detail": event.get("detail", "")},
                authority_changed=False,
            )
        if kind == "bad-progress":
            return CommandWorkspaceTransition(
                _State("intake"),
                authority_changed=False,
            )
        if kind == "terminal-without-authority":
            return CommandWorkspaceTransition(
                _State("receipt"),
                terminal=True,
                authority_changed=False,
            )
        return CommandWorkspaceTransition(_State("preview"))


def _host(adapter: _Adapter | None = None) -> tuple[CommandWorkspaceHost, _Adapter]:
    resolved = adapter or _Adapter()
    host = CommandWorkspaceHost()
    host.register(resolved)
    return host, resolved


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    source = repo / "src"
    source.mkdir()
    (source / "pricing.py").write_text("PRICE = 100\n")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_pricing.py").write_text("def test_price(): pass\n")
    monkeypatch.chdir(repo)
    return repo


def _server(repo: Path) -> AttuneMCPServer:
    with (
        patch.object(AttuneMCPServer, "_register_plugin_tools"),
        patch("attune.mcp.version_check.check_for_updates", return_value=None),
    ):
        return AttuneMCPServer(workspace_root=str(repo))


def test_registration_rejects_unknown_duplicate_and_invalid_adapters() -> None:
    host, adapter = _host()
    assert host.adapter("example") is adapter
    assert host.get("missing") is None

    with pytest.raises(CommandWorkspaceError, match="duplicate"):
        host.register(adapter)
    with pytest.raises(CommandWorkspaceError, match="unknown"):
        host.adapter("missing")

    invalid = _Adapter()
    invalid.adapter_id = "Bad Adapter"
    with pytest.raises(CommandWorkspaceError, match="adapter_id"):
        host.register(invalid)
    with pytest.raises(CommandWorkspaceError, match="required protocol"):
        host.register(object())

    create_only = type(
        "CreateOnly",
        (),
        {"adapter_id": "create_only", "schema_version": 1, "create": lambda *args: None},
    )()
    with pytest.raises(CommandWorkspaceError, match="required protocol"):
        host.register(create_only)


@pytest.mark.parametrize("schema_version", [True, 0])
def test_registration_rejects_invalid_schema_versions(schema_version: object) -> None:
    adapter = _Adapter()
    adapter.schema_version = schema_version
    with pytest.raises(CommandWorkspaceError, match="schema_version"):
        CommandWorkspaceHost().register(adapter)


def test_projection_and_transition_validate_portable_contract() -> None:
    preview = workspace_from_dict(
        {
            "id": "preview",
            "title": "Preview",
            "actions": [{"id": "go", "label": "Go"}],
        }
    )
    with pytest.raises(ValueError, match="SHA-256"):
        CommandWorkspaceProjection(preview)
    with pytest.raises(TypeError, match="WorkspaceView"):
        CommandWorkspaceProjection("not-a-view")
    with pytest.raises(TypeError, match="hash must be a string"):
        CommandWorkspaceProjection(preview, 7)
    receipt = workspace_from_dict({"id": "receipt", "title": "Receipt"})
    with pytest.raises(ValueError, match="must be a SHA-256"):
        CommandWorkspaceProjection(receipt, "bad")
    with pytest.raises(TypeError, match="terminal flag"):
        CommandWorkspaceTransition(_State("preview"), terminal="yes")
    with pytest.raises(TypeError, match="result must be a mapping"):
        CommandWorkspaceTransition(_State("preview"), result=[])


@pytest.mark.asyncio
async def test_open_renders_widget_markdown_and_headless_binding_parity() -> None:
    host, _ = _host()
    render = await host.open("example", {})

    assert render.record.revision == 0
    assert render.record.adapter_version == 1
    assert render.record.binding.contract_hash == render.record.contract_hash
    for action_id in ("edit", "approve"):
        assert f'data-workspace-action="{action_id}"' in render.html
        quoted_action = f"{chr(96)}{action_id}{chr(96)}"
        assert quoted_action in render.markdown
    public = render.to_dict()
    assert public["action_nonce"] == render.record.action_nonce
    assert public["view"] == "preview"
    assert render.record.workspace_id in render.html
    assert render.record.workspace_id in render.markdown


@pytest.mark.asyncio
async def test_edit_invalidates_authority_and_adapter_controls_reentry() -> None:
    host, _ = _host()
    first = await host.open("example", {})
    edited = await host.collect(_payload(first, "edit"))

    assert edited.record.revision == 1
    assert edited.record.view.id.value == "intake"
    assert edited.record.action_nonce == ""
    with pytest.raises(CommandWorkspaceError, match="awaiting a bound action"):
        _ = edited.record.binding

    second = await host.open(
        "example",
        {},
        workspace_id=first.record.workspace_id,
    )
    assert second.record.revision == 2
    assert second.record.action_nonce != first.record.action_nonce

    with pytest.raises(CommandWorkspaceError, match="select edit"):
        await host.open(
            "example",
            {},
            workspace_id=second.record.workspace_id,
        )


@pytest.mark.asyncio
async def test_altered_unknown_and_replayed_actions_fail_without_mutation() -> None:
    host, _ = _host()
    render = await host.open("example", {})
    original = host.get(render.record.workspace_id)
    base = _payload(render, "approve", confirmed=True)

    for change in (
        {"revision": 9},
        {"action_nonce": "n" * 32},
        {"contract_hash": "0" * 64},
        {"action": "unknown"},
    ):
        with pytest.raises(CommandWorkspaceError):
            await host.collect({**base, **change})
        assert host.get(render.record.workspace_id) == original

    result = await host.collect(base)
    assert result.record.terminal is True
    assert result.result == {"approved_value": "example"}
    assert result.to_dict()["result"] == {"approved_value": "example"}
    with pytest.raises(CommandWorkspaceError, match="already consumed"):
        await host.collect(base)
    with pytest.raises(CommandWorkspaceError, match="terminal.*replaced"):
        await host.open(
            "example",
            {},
            workspace_id=render.record.workspace_id,
        )


@pytest.mark.asyncio
async def test_concurrent_confirmations_publish_one_terminal_transition() -> None:
    host, _ = _host()
    render = await host.open("example", {})
    payload = _payload(render, "approve", confirmed=True)

    results = await asyncio.gather(
        host.collect(payload),
        host.collect(payload),
        return_exceptions=True,
    )

    accepted = [item for item in results if not isinstance(item, Exception)]
    rejected = [item for item in results if isinstance(item, CommandWorkspaceError)]
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert accepted[0].record.revision == 1
    assert accepted[0].record.view.id.value == "receipt"
    assert accepted[0].record.action_nonce == ""


@pytest.mark.asyncio
async def test_projection_drift_fails_before_adapter_apply() -> None:
    adapter = _Adapter()
    host, _ = _host(adapter)
    render = await host.open("example", {})
    adapter.project_suffix = " changed"

    with pytest.raises(CommandWorkspaceError, match="view changed"):
        await host.collect(_payload(render, "edit"))

    assert host.get(render.record.workspace_id) == render.record


@pytest.mark.asyncio
async def test_contract_drift_and_terminal_actions_fail_before_publication() -> None:
    adapter = _Adapter()
    host, _ = _host(adapter)
    render = await host.open("example", {})
    adapter.contract_suffix = "changed"
    with pytest.raises(CommandWorkspaceError, match="contract changed"):
        await host.collect(_payload(render, "edit"))
    assert host.get(render.record.workspace_id) == render.record


@pytest.mark.asyncio
async def test_progress_publication_has_independent_event_sequence() -> None:
    host, _ = _host()
    render = await host.open("example", {})
    progress = await host.publish(
        render.record.workspace_id,
        {"kind": "progress", "detail": "seat 1 complete"},
    )

    assert progress.record.revision == render.record.revision
    assert progress.record.action_nonce == render.record.action_nonce
    assert progress.record.event_sequence == 1
    assert progress.result == {"detail": "seat 1 complete"}

    changed = await host.publish(
        render.record.workspace_id,
        {"kind": "checkpoint"},
    )
    assert changed.record.revision == render.record.revision + 1
    assert changed.record.event_sequence == 2
    assert changed.record.action_nonce != render.record.action_nonce

    edited = await host.collect(_payload(changed.render, "edit"))
    assert edited.record.event_sequence == 2


@pytest.mark.asyncio
async def test_progress_publication_cannot_smuggle_authority_changes() -> None:
    host, adapter = _host()
    render = await host.open("example", {})
    with pytest.raises(CommandWorkspaceError, match="changed action authority"):
        await host.publish(render.record.workspace_id, {"kind": "bad-progress"})
    with pytest.raises(CommandWorkspaceError, match="must change authority"):
        await host.publish(
            render.record.workspace_id,
            {"kind": "terminal-without-authority"},
        )
    with pytest.raises(CommandWorkspaceError, match="event must be a mapping"):
        await host.publish(render.record.workspace_id, [])
    with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
        await host.publish("workspace-missing", {"kind": "progress"})

    adapter.contract_suffix = ""
    adapter.receipt_actions = True
    with pytest.raises(CommandWorkspaceError, match="terminal.*cannot expose actions"):
        await host.collect(_payload(render, "approve", confirmed=True))
    assert host.get(render.record.workspace_id) == render.record


@pytest.mark.asyncio
async def test_open_rejects_unknown_workspace_bad_intake_and_adapter_mismatch() -> None:
    host, adapter = _host()
    with pytest.raises(CommandWorkspaceError, match="unknown command workspace_id"):
        await host.open("example", {}, workspace_id="workspace-missing")
    with pytest.raises(CommandWorkspaceError, match="intake must be a mapping"):
        await host.open("example", [])

    other = _Adapter()
    other.adapter_id = "other"
    host.register(other)
    render = await host.open("example", {})
    with pytest.raises(CommandWorkspaceError, match="canonical state"):
        await host.open("other", {}, workspace_id=render.record.workspace_id)
    with pytest.raises(CommandWorkspaceError, match="requested tool"):
        await host.collect(
            _payload(render, "edit"),
            expected_adapter_id="other",
        )
    adapter.schema_version = 2
    with pytest.raises(CommandWorkspaceError, match="version changed"):
        await host.collect(_payload(render, "edit"))
    with pytest.raises(CommandWorkspaceError, match="version changed"):
        await host.open("example", {}, workspace_id=render.record.workspace_id)
    with pytest.raises(CommandWorkspaceError, match="must be a mapping"):
        await host.collect([])
    with pytest.raises(CommandWorkspaceError, match="requires workspace_id"):
        await host.collect({})
    with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
        await host.collect({"workspace_id": "workspace-missing"})


@pytest.mark.asyncio
async def test_generic_mcp_tools_run_fix_through_the_shared_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, monkeypatch)
    server = _server(repo)
    assert "command_workspace_open" in server.tools
    assert "command_workspace_collect_action" in server.tools
    missing_adapter = await server.call_tool("command_workspace_open", {"intake": {}})
    assert missing_adapter["success"] is False
    unknown_adapter = await server.call_tool(
        "command_workspace_open",
        {"adapter_id": "missing", "intake": {}},
    )
    assert unknown_adapter["success"] is False
    unknown_action = await server.call_tool(
        "command_workspace_collect_action",
        {"response": {}},
    )
    assert unknown_action["success"] is False
    invalid_fix = await server.call_tool(
        "fix_workspace_preview",
        {"answers": {}},
    )
    assert invalid_fix["success"] is False

    opened = await server.call_tool(
        "command_workspace_open",
        {
            "adapter_id": "fix",
            "intake": {
                "request": "make boundary orders bulk",
                "scope": "src/pricing.py",
                "probes": ["pytest tests/test_pricing.py -q"],
            },
        },
    )
    assert opened["success"] is True
    assert opened["adapter_id"] == "fix"
    assert "run_fix" in opened["html"]
    assert f"{chr(96)}run_fix{chr(96)}" in opened["markdown"]

    record = server._command_workspaces.get(opened["workspace_id"])
    assert record is not None
    state = server._fix_workspace_adapter.compatibility_state(record)
    assert isinstance(state, FixWorkspaceState)
    response = {
        "__elicitation_response__": True,
        "title": "Fix preview",
        "workspace_id": opened["workspace_id"],
        "revision": opened["revision"],
        "view": "preview",
        "action": "run_fix",
        "action_nonce": opened["action_nonce"],
        "contract_hash": opened["contract_hash"],
        "confirmed": True,
    }
    collected = await server.call_tool(
        "command_workspace_collect_action",
        {"response": response},
    )

    assert collected["success"] is True
    assert collected["terminal"] is True
    assert collected["view"] == "receipt"
    assert collected["result"]["approved"] is True
    assert collected["result"]["approved_command_argv"][-1] == "--run"
