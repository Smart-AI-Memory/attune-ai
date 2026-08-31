"""Behavioral coverage for the Roundtable command workspace."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.mcp.server import AttuneMCPServer
from attune.roundtable.rotation import CANONICAL_SEATS
from attune.roundtable.workspace import (
    RoundtableCandidate,
    RoundtableRuling,
    RoundtableSeatReceipt,
    RoundtableWorkspaceAdapter,
    RoundtableWorkspaceState,
)


def _host() -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(RoundtableWorkspaceAdapter())
    return host


def _intake(*, max_invocations: int = 9) -> dict[str, object]:
    return {
        "question": "Should all commands use the shared renderer?",
        "thread_id": "shared-renderer-test",
        "expected_rounds": 3,
        "max_invocations": max_invocations,
    }


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


def _receipts(round_number: int = 1) -> list[dict[str, object]]:
    return [
        {
            "seat": seat,
            "status": "complete",
            "message_id": index + (round_number - 1) * 3,
            "detail": f"{seat} completed round {round_number}",
            "compiler_clean": True,
        }
        for index, seat in enumerate(CANONICAL_SEATS, start=1)
    ]


def _response(action: str, *, confirmed: bool = False) -> WorkspaceActionResponse:
    return WorkspaceActionResponse(
        WorkspaceViewId.EXECUTION,
        action,
        confirmed,
    )


async def _running(host: CommandWorkspaceHost, *, max_invocations: int = 9):
    preview = await host.open("roundtable", _intake(max_invocations=max_invocations))
    return await host.collect(_payload(preview, "start_roundtable", confirmed=True))


async def _triage(host: CommandWorkspaceHost, count: int = 7):
    running = await _running(host)
    checkpoint = await host.publish(
        running.record.workspace_id,
        {"kind": "round_complete", "receipts": _receipts()},
    )
    synthesizing = await host.collect(_payload(checkpoint, "synthesize"))
    candidates = [
        {
            "message_id": index,
            "title": f"Candidate {index}",
            "detail": f"Proposal detail {index}",
        }
        for index in range(10, 10 + count)
    ]
    return await host.publish(
        synthesizing.record.workspace_id,
        {"kind": "synthesis", "body": "Bounded synthesis", "candidates": candidates},
    )


@pytest.mark.asyncio
async def test_preview_renders_fixed_roster_spend_cap_and_fallback() -> None:
    preview = await _host().open("roundtable", _intake())

    assert preview.record.view.id.value == "preview"
    assert all(seat in preview.html for seat in CANONICAL_SEATS)
    assert all(seat in preview.markdown for seat in CANONICAL_SEATS)
    assert "9" in preview.markdown
    assert "start_roundtable" in preview.html
    assert "`start_roundtable`" in preview.markdown


@pytest.mark.asyncio
async def test_start_requires_confirmation_and_invocation_budget() -> None:
    host = _host()
    preview = await host.open("roundtable", _intake())
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "start_roundtable"))

    running = await host.collect(_payload(preview, "start_roundtable", confirmed=True))
    assert running.record.state.stage == "running"
    assert running.result == {"delegate": "roundtable.run_round", "round": 1}

    too_small = await host.open("roundtable", _intake(max_invocations=2))
    with pytest.raises(CommandWorkspaceError, match="fixed roster"):
        await host.collect(_payload(too_small, "start_roundtable", confirmed=True))


@pytest.mark.asyncio
async def test_explicit_edit_allows_canonical_intake_replacement() -> None:
    host = _host()
    preview = await host.open("roundtable", _intake())
    intake = await host.collect(_payload(preview, "edit_roundtable"))
    assert intake.record.state.stage == "intake"
    revised = _intake()
    revised["question"] = "Revised question"
    replacement = await host.open(
        "roundtable",
        revised,
        workspace_id=preview.record.workspace_id,
    )
    assert replacement.record.state.question == "Revised question"
    assert replacement.record.revision == 2


@pytest.mark.asyncio
async def test_progress_keeps_action_authority_and_advances_event_sequence() -> None:
    host = _host()
    running = await _running(host)
    progress = await host.publish(
        running.record.workspace_id,
        {
            "kind": "seat_progress",
            "receipt": {
                "seat": "claude",
                "status": "running",
                "detail": "drafting",
                "compiler_clean": True,
            },
        },
    )

    assert progress.record.revision == running.record.revision
    assert progress.record.action_nonce == running.record.action_nonce
    assert progress.record.event_sequence == running.record.event_sequence + 1
    assert "drafting" in progress.render.markdown


@pytest.mark.asyncio
async def test_compiler_dirty_and_incomplete_roster_fail_without_mutation() -> None:
    host = _host()
    running = await _running(host)
    with pytest.raises(CommandWorkspaceError, match="compiler-dirty"):
        await host.publish(
            running.record.workspace_id,
            {
                "kind": "seat_progress",
                "receipt": {
                    "seat": "codex",
                    "status": "complete",
                    "message_id": 4,
                    "compiler_clean": False,
                },
            },
        )
    with pytest.raises(CommandWorkspaceError, match="fixed Roundtable roster"):
        await host.publish(
            running.record.workspace_id,
            {"kind": "round_complete", "receipts": _receipts()[:2]},
        )
    assert host.get(running.record.workspace_id) == running.record


@pytest.mark.asyncio
async def test_nested_round_checkpoint_rejects_stale_action_and_honors_cap() -> None:
    host = _host()
    running = await _running(host, max_invocations=6)
    checkpoint = await host.publish(
        running.record.workspace_id,
        {"kind": "round_complete", "receipts": _receipts()},
    )
    stale = _payload(checkpoint, "next_round")
    second = await host.collect(stale)
    assert second.record.state.round_number == 2
    assert second.record.state.seat_receipts == ()
    with pytest.raises(
        CommandWorkspaceError,
        match="revision|nonce|authority|not awaiting a bound action",
    ):
        await host.collect(stale)

    final_checkpoint = await host.publish(
        second.record.workspace_id,
        {"kind": "round_complete", "receipts": _receipts(2)},
    )
    assert [action.id for action in final_checkpoint.record.view.actions] == ["synthesize"]


@pytest.mark.asyncio
async def test_seven_candidates_are_paginated_and_each_ruling_is_bound() -> None:
    host = _host()
    current = await _triage(host, 7)
    first_payload = _payload(current, "promote", confirmed=True)

    assert "Item 1 of 7" in current.render.markdown
    assert "Proposal detail 10" in current.render.markdown
    assert "Proposal detail 11" not in current.render.markdown
    assert "Proposal detail 11" not in current.render.html

    current = await host.collect(first_payload)
    with pytest.raises(CommandWorkspaceError, match="revision|nonce|authority"):
        await host.collect(first_payload)
    assert "Item 2 of 7" in current.render.markdown

    for _ in range(6):
        current = await host.collect(_payload(current, "decline"))

    state = current.record.state
    assert current.record.terminal is True
    assert state.stage == "receipt"
    assert state.promoted_ids == (10,)
    assert "Promoted message ids" in current.render.markdown
    assert "10" in current.render.markdown


@pytest.mark.asyncio
async def test_promotion_requires_confirmation_and_another_round_reenters_execution() -> None:
    host = _host()
    triage = await _triage(host, 2)
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(triage, "promote"))

    second_candidate = await host.collect(_payload(triage, "decline"))
    running = await host.collect(_payload(second_candidate, "another_round"))
    assert running.record.state.stage == "running"
    assert running.record.state.round_number == 2
    assert running.record.state.seat_receipts == ()
    assert running.record.state.candidates == ()
    assert running.record.state.triage_index == 0
    assert running.record.state.rulings == (RoundtableRuling(10, "decline"),)
    assert running.result["delegate"] == "roundtable.run_round"


def test_state_rejects_duplicate_receipts_candidates_and_dirty_compiler() -> None:
    receipt = RoundtableSeatReceipt("claude", "complete", 1, message_id=1)
    with pytest.raises(CommandWorkspaceError, match="one receipt per seat"):
        RoundtableWorkspaceState(
            **_intake(),
            seat_receipts=(receipt, receipt),
        )
    candidate = RoundtableCandidate(1, "A", "B")
    with pytest.raises(CommandWorkspaceError, match="unique"):
        RoundtableWorkspaceState(
            **_intake(),
            candidates=(candidate, candidate),
        )
    with pytest.raises(CommandWorkspaceError, match="compiler-dirty"):
        RoundtableSeatReceipt("claude", "complete", 1, compiler_clean=False)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("missing", "complete", 1), "unknown Roundtable seat"),
        (("claude", "unknown", 1), "invalid seat status"),
        (("claude", "complete", 0), "receipt round"),
        (("claude", "complete", 1, 0), "message id must be positive"),
    ],
)
def test_seat_receipt_value_validation(args: tuple[object, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        RoundtableSeatReceipt(*args)


def test_candidate_and_ruling_value_validation() -> None:
    with pytest.raises(CommandWorkspaceError, match="candidate message id"):
        RoundtableCandidate(0, "title", "detail")
    with pytest.raises(CommandWorkspaceError, match="requires title and detail"):
        RoundtableCandidate(1, "", "detail")
    with pytest.raises(CommandWorkspaceError, match="ruling message id"):
        RoundtableRuling(0, "decline")
    with pytest.raises(CommandWorkspaceError, match="ruling disposition"):
        RoundtableRuling(1, "unknown")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"question": ""}, "question must not be empty"),
        ({"thread_id": "has space"}, "thread_id is invalid"),
        ({"expected_rounds": 4}, "expected_rounds must be 1..3"),
        ({"max_invocations": 0}, "max_invocations must be positive"),
        ({"stage": "missing"}, "stage is invalid"),
        ({"round_number": 4}, "round_number must be 1..3"),
        (
            {
                "candidates": tuple(
                    RoundtableCandidate(index, f"t{index}", "detail") for index in range(1, 9)
                )
            },
            "at most 7",
        ),
        ({"triage_index": 1}, "triage_index is out of range"),
        (
            {
                "rulings": (
                    RoundtableRuling(1, "decline"),
                    RoundtableRuling(1, "promote"),
                )
            },
            "ruled only once",
        ),
    ],
)
def test_workspace_state_value_validation(changes: dict[str, object], message: str) -> None:
    values = _intake()
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        RoundtableWorkspaceState(**values)


def test_adapter_intake_and_type_validation() -> None:
    adapter = RoundtableWorkspaceAdapter()
    preview = adapter.create(_intake())
    with pytest.raises(CommandWorkspaceError, match="select edit_roundtable"):
        adapter.create(_intake(), prior_state=preview)
    with pytest.raises(CommandWorkspaceError, match="unknown Roundtable intake"):
        adapter.create({**_intake(), "extra": True})
    with pytest.raises(CommandWorkspaceError, match="expected_rounds must be an integer"):
        adapter.create({**_intake(), "expected_rounds": "three"})
    with pytest.raises(CommandWorkspaceError, match="max_invocations must be an integer"):
        adapter.create({**_intake(), "max_invocations": True})
    for method, args in (
        (adapter.project, (object(),)),
        (adapter.apply, (object(), _response("decline"))),
        (adapter.publish, (object(), {"kind": "x"})),
    ):
        with pytest.raises(CommandWorkspaceError, match="incompatible state"):
            method(*args)


def test_adapter_rejects_illegal_actions_and_events() -> None:
    adapter = RoundtableWorkspaceAdapter()
    preview = adapter.create(_intake())
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, _response("unknown"))
    with pytest.raises(CommandWorkspaceError, match="active Roundtable stage"):
        adapter.publish(preview, {"kind": "seat_progress", "receipt": {}})

    running = adapter.apply(preview, _response("start_roundtable", confirmed=True)).state
    with pytest.raises(CommandWorkspaceError, match="receipt mapping"):
        adapter.publish(running, {"kind": "seat_progress", "receipt": []})
    with pytest.raises(CommandWorkspaceError, match="message_id must be an integer"):
        adapter.publish(
            running,
            {
                "kind": "seat_progress",
                "receipt": {
                    "seat": "claude",
                    "status": "complete",
                    "message_id": True,
                },
            },
        )
    for bad in (None, "receipts", [1, 2, 3]):
        with pytest.raises(CommandWorkspaceError, match="receipt"):
            adapter.publish(running, {"kind": "round_complete", "receipts": bad})
    with pytest.raises(CommandWorkspaceError, match="followups must be a list"):
        adapter.publish(
            running,
            {"kind": "round_complete", "receipts": _receipts(), "followups": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="unknown Roundtable event"):
        adapter.publish(running, {"kind": "missing"})


def test_synthesis_validation_and_zero_candidate_terminal_receipt() -> None:
    adapter = RoundtableWorkspaceAdapter()
    preview = adapter.create(_intake())
    running = adapter.apply(preview, _response("start_roundtable", confirmed=True)).state
    checkpoint = adapter.publish(
        running,
        {"kind": "round_complete", "receipts": _receipts()},
    ).state
    with pytest.raises(CommandWorkspaceError, match="running round"):
        adapter.publish(checkpoint, {"kind": "round_complete", "receipts": _receipts()})
    with pytest.raises(CommandWorkspaceError, match="synthesizing stage"):
        adapter.publish(checkpoint, {"kind": "synthesis", "body": "x"})
    synthesizing = adapter.apply(checkpoint, _response("synthesize")).state
    with pytest.raises(CommandWorkspaceError, match="must not be empty"):
        adapter.publish(synthesizing, {"kind": "synthesis", "body": ""})
    with pytest.raises(CommandWorkspaceError, match="candidates must be a list"):
        adapter.publish(
            synthesizing,
            {"kind": "synthesis", "body": "x", "candidates": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="candidate is not a mapping"):
        adapter.publish(
            synthesizing,
            {"kind": "synthesis", "body": "x", "candidates": [1]},
        )
    with pytest.raises(CommandWorkspaceError, match="candidate message_id must be an integer"):
        adapter.publish(
            synthesizing,
            {
                "kind": "synthesis",
                "body": "x",
                "candidates": [{"message_id": True, "title": "a", "detail": "b"}],
            },
        )

    terminal = adapter.publish(
        synthesizing,
        {"kind": "synthesis", "body": "No candidates", "candidates": []},
    )
    assert terminal.terminal is True
    receipt = adapter.project(terminal.state)
    assert not receipt.view.actions


def test_direct_triage_guards_exhausted_invalid_and_capped_paths() -> None:
    adapter = RoundtableWorkspaceAdapter()
    candidate = RoundtableCandidate(7, "Candidate", "Detail")
    exhausted = RoundtableWorkspaceState(
        **_intake(),
        stage="triage",
        candidates=(candidate,),
        triage_index=1,
    )
    with pytest.raises(CommandWorkspaceError, match="no current candidate"):
        adapter.apply(exhausted, _response("decline"))
    active = RoundtableWorkspaceState(
        **_intake(max_invocations=3),
        stage="triage",
        candidates=(candidate,),
    )
    with pytest.raises(CommandWorkspaceError, match="unknown Roundtable disposition"):
        adapter.apply(active, _response("unknown"))
    with pytest.raises(CommandWorkspaceError, match="explicit chair confirmation"):
        adapter.apply(active, _response("promote"))
    with pytest.raises(CommandWorkspaceError, match="ceiling or invocation cap"):
        adapter.apply(active, _response("another_round"))


@pytest.mark.asyncio
async def test_generic_server_registers_and_runs_roundtable_adapter(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    with (
        patch.object(AttuneMCPServer, "_register_plugin_tools"),
        patch("attune.mcp.version_check.check_for_updates", return_value=None),
    ):
        server = AttuneMCPServer(workspace_root=str(repo))

    opened = await server.call_tool(
        "command_workspace_open",
        {"adapter_id": "roundtable", "intake": _intake()},
    )
    assert opened["success"] is True
    response = {
        "__elicitation_response__": True,
        "title": "Roundtable spend preview",
        "view": "preview",
        "action": "start_roundtable",
        "confirmed": True,
        "workspace_id": opened["workspace_id"],
        "revision": opened["revision"],
        "action_nonce": opened["action_nonce"],
        "contract_hash": opened["contract_hash"],
    }
    started = await server.call_tool(
        "command_workspace_collect_action",
        {"response": response},
    )
    assert started["success"] is True
    published = await server.call_tool(
        "command_workspace_publish",
        {
            "workspace_id": opened["workspace_id"],
            "event": {"kind": "round_complete", "receipts": _receipts()},
        },
    )
    assert published["success"] is True
    assert published["view"] == "execution"
