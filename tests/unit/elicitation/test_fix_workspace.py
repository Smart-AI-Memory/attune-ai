"""Behavioral coverage for canonical Fix workspace authority."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.fix_workspace import (
    FixAdapterState,
    FixWorkspaceAdapter,
    FixWorkspaceError,
    FixWorkspaceState,
    preview_workspace_dict,
    validate_fix_workspace_action,
)
from attune.mcp.server import AttuneMCPServer


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


def _answers(request: str = "make boundary orders bulk") -> dict:
    return {
        "request": request,
        "scope": "src/pricing.py",
        "probes": ["pytest tests/test_pricing.py -q"],
    }


def _response(
    state: FixWorkspaceState,
    action: str = "run_fix",
    *,
    confirmed: bool = True,
) -> dict:
    return {
        "__elicitation_response__": True,
        "title": "Fix preview",
        "workspace_id": state.workspace_id,
        "revision": state.revision,
        "view": "preview",
        "action": action,
        "action_nonce": state.action_nonce,
        "contract_hash": state.contract_hash,
        "confirmed": confirmed,
    }


def _server(repo: Path) -> AttuneMCPServer:
    with (
        patch.object(AttuneMCPServer, "_register_plugin_tools"),
        patch("attune.mcp.version_check.check_for_updates", return_value=None),
    ):
        return AttuneMCPServer(workspace_root=str(repo))


def test_state_and_preview_round_trip_without_losing_order_or_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    answers = _answers("preserve  two spaces and café")
    answers["probes"].append("python -m pytest tests/test_pricing.py")
    state = FixWorkspaceState.create_preview(answers)

    restored = FixWorkspaceState.from_json(state.to_json())

    assert restored == state
    assert restored.preview is not None
    assert restored.preview.goal == "preserve  two spaces and café"
    assert [probe.argv[0] for probe in restored.preview.probes] == ["pytest", "python"]
    assert restored.preview.contract_hash() == state.contract_hash


@pytest.mark.parametrize(
    "answers",
    [
        [],
        {},
        {"request": "x", "scope": "src/pricing.py", "probes": ["pytest x"], "extra": 1},
        {"request": "", "scope": "src/pricing.py", "probes": ["pytest x"]},
        {"request": "x", "scope": "", "probes": ["pytest x"]},
        {"request": "x", "scope": "src/pricing.py", "probes": 7},
        {"request": "x", "scope": "src/pricing.py", "probes": []},
    ],
)
def test_invalid_intake_answers_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answers,
) -> None:
    _repo(tmp_path, monkeypatch)
    with pytest.raises(FixWorkspaceError):
        FixWorkspaceState.create_preview(answers)


def test_string_probe_is_normalized_to_one_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    answers = _answers()
    answers["probes"] = "pytest tests/test_pricing.py"

    state = FixWorkspaceState.create_preview(answers)

    assert state.validated_answers["probes"] == ["pytest tests/test_pricing.py"]


def test_unbuildable_scope_returns_workspace_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    answers = _answers()
    answers["scope"] = "../../outside"

    with pytest.raises(FixWorkspaceError, match="invalid --scope"):
        FixWorkspaceState.create_preview(answers)


def test_render_projection_is_disposable_and_not_hashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    assert state.preview is not None
    rendered = preview_workspace_dict(state.preview)

    rendered["title"] = "A different disposable title"

    assert state.preview.contract_hash() == state.contract_hash


def test_restore_rejects_mutated_preview_under_old_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    raw = FixWorkspaceState.create_preview(_answers()).to_dict()
    raw["preview"]["goal"] = "silently widened goal"

    with pytest.raises(FixWorkspaceError, match="contract hash"):
        FixWorkspaceState.from_dict(raw)


def test_restore_rejects_invalid_json_and_state_shape() -> None:
    with pytest.raises(FixWorkspaceError, match="not valid JSON"):
        FixWorkspaceState.from_json("{")
    with pytest.raises(FixWorkspaceError, match="missing or unknown"):
        FixWorkspaceState.from_dict({})


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"workspace_id": "bad id"},
        {"revision": True},
        {"revision": -1},
        {"view": "receipt"},
        {"action_nonce": "short"},
        {"approved_contract_hash": None},
        {"approved_contract_hash": "0" * 64},
    ],
)
def test_invalid_state_fields_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict,
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    with pytest.raises(FixWorkspaceError):
        replace(state, **changes)


def test_incoherent_state_combinations_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    with pytest.raises(FixWorkspaceError, match="cannot be stored"):
        replace(state, view="intake")
    with pytest.raises(FixWorkspaceError, match="cannot retain preview authority"):
        replace(state, view="intake", preview=None)
    with pytest.raises(FixWorkspaceError, match="cannot retain an action nonce"):
        replace(state, approved_contract_hash=state.contract_hash)
    with pytest.raises(FixWorkspaceError, match="wrong type"):
        replace(state, preview="not-a-preview")


def test_noncanonical_answer_serialization_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    pretty = json.dumps(state.validated_answers, indent=2)
    with pytest.raises(FixWorkspaceError, match="canonically serialized"):
        replace(state, validated_answers_json=pretty)


def test_run_action_recomputes_hash_consumes_nonce_and_never_executes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())

    result = validate_fix_workspace_action(state, _response(state))

    assert result.action == "run_fix"
    assert result.state.approved_contract_hash == state.contract_hash
    assert result.state.action_nonce == ""
    assert result.state.revision == state.revision + 1
    assert result.approved_command_argv[-1] == "--run"
    assert result.to_dict()["execution_started"] is False
    with pytest.raises(FixWorkspaceError, match="already consumed"):
        validate_fix_workspace_action(result.state, _response(state))


def test_action_time_rebuild_rejects_changed_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    mutated_answers = json.dumps(
        _answers("broadened after rendering"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    mutated = replace(state, validated_answers_json=mutated_answers)

    with pytest.raises(FixWorkspaceError, match="changed after it was rendered"):
        validate_fix_workspace_action(mutated, _response(mutated))


def test_action_time_rebuild_is_authoritative_over_stored_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    assert state.preview is not None
    rebuilt = replace(state.preview, goal="different canonical goal")

    with patch(
        "attune.elicitation.fix_workspace._preview_from_answers",
        return_value=rebuilt,
    ) as rebuild:
        with pytest.raises(FixWorkspaceError, match="changed after it was rendered"):
            validate_fix_workspace_action(state, _response(state))

    rebuild.assert_called_once_with(state.validated_answers)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"action": "delete_repo"}, "not allowed"),
        ({"workspace_id": "fix-other"}, "workspace id does not match"),
        ({"contract_hash": "0" * 64}, "contract hash does not match"),
        ({"revision": 99}, "revision does not match"),
        ({"action_nonce": "n" * 32}, "nonce does not match"),
        ({"confirmed": False}, "requires explicit confirmation"),
    ],
)
def test_unknown_mutated_stale_and_unconfirmed_actions_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: dict,
    problem: str,
) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())
    payload = {**_response(state), **change}

    with pytest.raises(FixWorkspaceError, match=problem):
        validate_fix_workspace_action(state, payload)


def test_edit_invalidates_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _repo(tmp_path, monkeypatch)
    state = FixWorkspaceState.create_preview(_answers())

    result = validate_fix_workspace_action(
        state,
        _response(state, "edit_contract", confirmed=False),
    )

    assert result.state.view == "intake"
    assert result.state.preview is None
    assert result.state.contract_hash == ""
    assert result.state.action_nonce == ""
    with pytest.raises(FixWorkspaceError, match="not awaiting"):
        validate_fix_workspace_action(result.state, _response(state))


def test_fix_adapter_state_rejects_incoherent_domain_combinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    adapter = FixWorkspaceAdapter()
    state = adapter.create(_answers())
    assert state.preview is not None

    invalid = (
        (state.validated_answers_json, state.preview, "unknown", ""),
        (state.validated_answers_json, state.preview, "intake", ""),
        (state.validated_answers_json, None, "preview", ""),
        (state.validated_answers_json, state.preview, "approved", "0" * 64),
        (state.validated_answers_json, state.preview, "preview", "0" * 64),
    )
    for args in invalid:
        with pytest.raises(FixWorkspaceError):
            FixAdapterState(*args)


def test_fix_adapter_rejects_invalid_reentry_state_and_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    adapter = FixWorkspaceAdapter()
    state = adapter.create(_answers())
    with pytest.raises(FixWorkspaceError, match="select edit_contract"):
        adapter.create(_answers(), prior_state=state)
    with pytest.raises(FixWorkspaceError, match="incompatible state"):
        adapter.project("not-fix-state")
    with pytest.raises(FixWorkspaceError, match="not awaiting"):
        adapter.apply(
            "not-fix-state",
            WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "run_fix", True),
        )
    with pytest.raises(FixWorkspaceError, match="unsupported Fix action"):
        adapter.apply(
            state,
            WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "unknown", True),
        )
    with pytest.raises(FixWorkspaceError, match="not a Fix command workspace"):
        adapter.compatibility_state("not-a-record")


def test_fix_adapter_rebuild_rejects_changed_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch)
    adapter = FixWorkspaceAdapter()
    state = adapter.create(_answers())
    assert state.preview is not None
    changed = replace(state.preview, goal="changed during approval")

    with patch(
        "attune.elicitation.fix_workspace._preview_from_answers",
        return_value=changed,
    ):
        with pytest.raises(FixWorkspaceError, match="changed after it was rendered"):
            adapter.apply(
                state,
                WorkspaceActionResponse(WorkspaceViewId.PREVIEW, "run_fix", True),
            )


@pytest.mark.asyncio
async def test_live_server_render_edit_rerender_run_and_replay_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-mocked render/collect boundary; only startup side effects are patched."""
    repo = _repo(tmp_path, monkeypatch)
    server = _server(repo)

    assert "fix_workspace_preview" in server.tools
    assert "fix_workspace_collect_action" in server.tools
    first = await server.call_tool("fix_workspace_preview", {"answers": _answers()})
    assert first["success"] is True
    assert "Fix preview" in first["html"]
    assert "data-confirm-armed" in first["html"]
    assert "window.confirm" not in first["html"]
    assert "Run Fix" in first["markdown"]
    assert first["mcp_app"] == {
        "resource_uri": "ui://attune-forms/dynamic-surface/v1",
        "collect_tool": "fix_workspace_collect_action",
        "collect_mode": "response",
    }
    assert first["execution_started"] is False
    first_state = FixWorkspaceState.from_dict(first["state"])

    edited = await server.call_tool(
        "fix_workspace_collect_action",
        {"response": _response(first_state, "edit_contract", confirmed=False)},
    )
    assert edited["success"] is True
    assert edited["state"]["view"] == "intake"

    second = await server.call_tool(
        "fix_workspace_preview",
        {
            "workspace_id": first_state.workspace_id,
            "answers": _answers("make boundary orders enterprise"),
        },
    )
    second_state = FixWorkspaceState.from_dict(second["state"])
    assert second_state.revision == 2
    assert second_state.contract_hash != first_state.contract_hash

    stale = await server.call_tool(
        "fix_workspace_collect_action", {"response": _response(first_state)}
    )
    assert stale["success"] is False

    approved = await server.call_tool(
        "fix_workspace_collect_action", {"response": _response(second_state)}
    )
    assert approved["success"] is True
    assert approved["approved"] is True
    assert approved["execution_started"] is False
    assert approved["approved_command_argv"][-1] == "--run"

    replay = await server.call_tool(
        "fix_workspace_collect_action", {"response": _response(second_state)}
    )
    assert replay["success"] is False
    assert any("consumed" in problem for problem in replay["problems"])


@pytest.mark.asyncio
async def test_concurrent_confirmations_return_at_most_one_approved_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, monkeypatch)
    server = _server(repo)
    rendered = await server.call_tool("fix_workspace_preview", {"answers": _answers()})
    state = FixWorkspaceState.from_dict(rendered["state"])

    results = await asyncio.gather(
        server.call_tool(
            "fix_workspace_collect_action",
            {"response": _response(state)},
        ),
        server.call_tool(
            "fix_workspace_collect_action",
            {"response": _response(state)},
        ),
    )

    approved = [result for result in results if result.get("approved")]
    assert len(approved) == 1
    assert approved[0]["approved_command_argv"][-1] == "--run"
    assert sum(result["success"] for result in results) == 1


@pytest.mark.asyncio
async def test_terminal_state_rejects_mutated_follow_up_without_state_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, monkeypatch)
    server = _server(repo)
    rendered = await server.call_tool("fix_workspace_preview", {"answers": _answers()})
    state = FixWorkspaceState.from_dict(rendered["state"])
    approved = await server.call_tool(
        "fix_workspace_collect_action",
        {"response": _response(state)},
    )
    assert approved["approved"] is True
    terminal_record = server._command_workspaces.get(state.workspace_id)
    assert terminal_record is not None

    mutated = _response(state)
    mutated.update(
        revision=state.revision + 1,
        action_nonce="n" * 32,
        contract_hash="0" * 64,
    )
    rejected = await server.call_tool(
        "fix_workspace_collect_action",
        {"response": mutated},
    )

    assert rejected["success"] is False
    assert server._command_workspaces.get(state.workspace_id) == terminal_record
    terminal_state = server._fix_workspace_adapter.compatibility_state(terminal_record)
    assert terminal_state.approved_contract_hash == state.contract_hash
    assert terminal_state.action_nonce == ""


@pytest.mark.asyncio
async def test_widget_markdown_and_headless_projection_have_action_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path, monkeypatch)
    server = _server(repo)
    rendered = await server.call_tool("fix_workspace_preview", {"answers": _answers()})
    state = FixWorkspaceState.from_dict(rendered["state"])
    assert state.preview is not None
    headless_actions = {action["id"] for action in preview_workspace_dict(state.preview)["actions"]}

    assert headless_actions == {"edit_contract", "run_fix"}
    for action_id in headless_actions:
        assert f'data-workspace-action="{action_id}"' in rendered["html"]
        assert f"`{action_id}`" in rendered["markdown"]
    for binding_value in (
        state.workspace_id,
        str(state.revision),
        state.action_nonce,
        state.contract_hash,
    ):
        assert binding_value in rendered["html"]
        assert binding_value in rendered["markdown"]
