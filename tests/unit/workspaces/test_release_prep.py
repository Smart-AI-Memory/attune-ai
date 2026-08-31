"""Behavioral coverage for the release-prep command workspace."""

from __future__ import annotations

from dataclasses import replace

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.workspaces.release_prep import (
    GATE_ORDER,
    ReleaseGateReceipt,
    ReleasePrepWorkspaceAdapter,
    ReleasePrepWorkspaceState,
)


def _host() -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(ReleasePrepWorkspaceAdapter())
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


def _response(action: str, *, confirmed: bool = False) -> WorkspaceActionResponse:
    return WorkspaceActionResponse(WorkspaceViewId.EXECUTION, action, confirmed)


def _receipt(name: str, status: str = "PASS") -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "detail": f"{name} {status.lower()}",
        "probe": f"probe-{name.lower()}",
    }


async def _running(host: CommandWorkspaceHost):
    preview = await host.open(
        "release-prep",
        {"version": "17.0.0", "scope": "full", "project_path": "."},
    )
    return await host.collect(_payload(preview, "start_release_prep", confirmed=True))


@pytest.mark.asyncio
async def test_preview_and_four_repeated_gate_approvals_reach_terminal_receipt() -> None:
    host = _host()
    preview = await host.open(
        "release-prep",
        {"version": "17.0.0", "scope": "full", "project_path": "."},
    )
    assert all(name in preview.markdown for name in GATE_ORDER)
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "start_release_prep"))
    current = await host.collect(_payload(preview, "start_release_prep", confirmed=True))
    for name in GATE_ORDER:
        prior = current
        current = await host.publish(
            current.record.workspace_id,
            {"kind": "gate_result", "receipt": _receipt(name)},
        )
        assert current.record.revision == prior.record.revision
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "assessment_complete", "recommendations": ["tag after approval"]},
    )
    assert current.record.state.review_gate == "Security"

    first = _payload(current, "accept_gate")
    current = await host.collect(first)
    with pytest.raises(CommandWorkspaceError, match="revision|nonce|authority"):
        await host.collect(first)
    for expected in GATE_ORDER[1:]:
        assert current.record.state.review_gate == expected
        current = await host.collect(_payload(current, "accept_gate"))
    assert current.record.state.stage == "approval"
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(current, "approve_release"))
    terminal = await host.collect(_payload(current, "approve_release", confirmed=True))
    assert terminal.record.terminal is True
    assert terminal.result["approved"] is True
    assert terminal.result["gate_receipts"] == list(GATE_ORDER)
    assert "Version 17.0.0 approved: True" in terminal.render.markdown


@pytest.mark.asyncio
async def test_missing_or_error_critical_gatekeeper_fails_closed() -> None:
    host = _host()
    current = await _running(host)
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "gate_result", "receipt": _receipt("Security", "ERROR")},
    )
    review = await host.publish(
        current.record.workspace_id,
        {"kind": "assessment_complete", "recommendations": []},
    )
    state = review.record.state
    assert state.gate("Security").passed is False
    assert {gate.name for gate in state.blockers} == {"Security", "Testing", "Versioning"}
    assert {gate.status for gate in state.gates} >= {"ERROR", "MISSING"}
    assert [action.id for action in review.record.view.actions] == ["rerun_gate"]
    with pytest.raises(CommandWorkspaceError, match="not allowed"):
        await host.collect(_payload(review, "accept_gate"))
    rerun = await host.collect(_payload(review, "rerun_gate"))
    assert rerun.record.state.stage == "running"
    assert rerun.result == {"delegate": "release-prep.rerun_gate", "gate": "Security"}


@pytest.mark.asyncio
async def test_noncritical_documentation_warning_requires_explicit_acceptance() -> None:
    host = _host()
    current = await _running(host)
    for name in GATE_ORDER:
        status = "FAIL" if name == "Documentation" else "PASS"
        current = await host.publish(
            current.record.workspace_id,
            {"kind": "gate_result", "receipt": _receipt(name, status)},
        )
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "assessment_complete", "recommendations": ["refresh docs"]},
    )
    current = await host.collect(_payload(current, "accept_gate"))
    current = await host.collect(_payload(current, "accept_gate"))
    assert current.record.state.review_gate == "Documentation"
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(current, "accept_warning"))
    current = await host.collect(_payload(current, "accept_warning", confirmed=True))
    current = await host.collect(_payload(current, "accept_gate"))
    assert current.record.state.stage == "approval"
    assert current.record.state.blockers == ()


@pytest.mark.asyncio
async def test_edit_replace_and_final_rerun_all(tmp_path) -> None:
    host = _host()
    preview = await host.open("release-prep", {})
    intake = await host.collect(_payload(preview, "edit_release"))
    assert intake.record.state.stage == "intake"
    preview = await host.open(
        "release-prep",
        {"version": "18.0.0", "scope": "security", "project_path": str(tmp_path)},
        workspace_id=preview.record.workspace_id,
    )
    current = await host.collect(_payload(preview, "start_release_prep", confirmed=True))
    for name in GATE_ORDER:
        current = await host.publish(
            current.record.workspace_id,
            {"kind": "gate_result", "receipt": _receipt(name)},
        )
    current = await host.publish(
        current.record.workspace_id,
        {"kind": "assessment_complete", "recommendations": []},
    )
    for _ in GATE_ORDER:
        current = await host.collect(_payload(current, "accept_gate"))
    rerun = await host.collect(_payload(current, "rerun_all"))
    assert rerun.record.state.stage == "running"
    assert rerun.record.state.gates == ()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("Missing", "PASS", "ok", "probe"), "gate name"),
        (("Security", "MAYBE", "ok", "probe"), "gate status"),
        (("Security", "PASS", "", "probe"), "detail"),
        (("Security", "PASS", "ok", ""), "probe"),
    ],
)
def test_gate_receipt_validation(args: tuple[str, ...], message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        ReleaseGateReceipt(*args)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"version": ""}, "version"),
        ({"scope": "unknown"}, "scope"),
        ({"project_path": ""}, "project_path"),
        ({"stage": "unknown"}, "stage"),
        (
            {
                "gates": (
                    ReleaseGateReceipt("Security", "PASS", "ok", "p"),
                    ReleaseGateReceipt("Security", "PASS", "ok", "p"),
                )
            },
            "unique",
        ),
        ({"accepted_gates": ("Missing",)}, "accepted gate"),
        ({"review_gate": "Missing"}, "review gate"),
    ],
)
def test_release_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {"version": "1.0.0", "scope": "full", "project_path": "."}
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        ReleasePrepWorkspaceState(**values)


def test_adapter_rejects_bad_intake_events_and_direct_illegal_paths() -> None:
    adapter = ReleasePrepWorkspaceAdapter()
    preview = adapter.create({})
    with pytest.raises(CommandWorkspaceError, match="select edit_release"):
        adapter.create({}, prior_state=preview)
    with pytest.raises(CommandWorkspaceError, match="unknown release-prep intake"):
        adapter.create({"extra": True})
    for method, args in (
        (adapter.project, (object(),)),
        (adapter.apply, (object(), _response("x"))),
        (adapter.publish, (object(), {"kind": "x"})),
    ):
        with pytest.raises(CommandWorkspaceError, match="incompatible state"):
            method(*args)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, _response("approve_release", confirmed=True))
    with pytest.raises(CommandWorkspaceError, match="running stage"):
        adapter.publish(preview, {"kind": "gate_result", "receipt": {}})
    running = adapter.apply(preview, _response("start_release_prep", confirmed=True)).state
    with pytest.raises(CommandWorkspaceError, match="receipt mapping"):
        adapter.publish(running, {"kind": "gate_result", "receipt": []})
    with pytest.raises(CommandWorkspaceError, match="recommendations must be a list"):
        adapter.publish(
            running,
            {"kind": "assessment_complete", "recommendations": "bad"},
        )
    omitted_recommendations = adapter.publish(
        running,
        {"kind": "assessment_complete"},
    )
    assert omitted_recommendations.state.recommendations == ()
    with pytest.raises(CommandWorkspaceError, match="unknown release-prep event"):
        adapter.publish(running, {"kind": "missing"})

    gate = ReleaseGateReceipt("Security", "FAIL", "bad", "probe")
    review = replace(running, stage="gate_review", gates=(gate,), review_gate="Security")
    with pytest.raises(CommandWorkspaceError, match="cannot be accepted"):
        adapter.apply(review, _response("accept_gate"))
    passed_review = replace(
        review,
        gates=(ReleaseGateReceipt("Security", "PASS", "ok", "probe"),),
    )
    with pytest.raises(CommandWorkspaceError, match="not legal for a passed gate"):
        adapter.apply(passed_review, _response("accept_warning", confirmed=True))
    warning_review = replace(
        review,
        gates=(ReleaseGateReceipt("Documentation", "FAIL", "warn", "probe"),),
        review_gate="Documentation",
    )
    with pytest.raises(CommandWorkspaceError, match="non-critical failed gate"):
        adapter.apply(warning_review, _response("accept_gate"))
    no_receipt = replace(review, gates=())
    with pytest.raises(CommandWorkspaceError, match="no current receipt"):
        adapter.apply(no_receipt, _response("rerun_gate"))
    with pytest.raises(CommandWorkspaceError, match="no current receipt"):
        adapter.project(no_receipt)

    blocked_approval = replace(
        running,
        stage="approval",
        gates=(gate,),
        accepted_gates=GATE_ORDER,
    )
    with pytest.raises(CommandWorkspaceError, match="blocked"):
        adapter.apply(blocked_approval, _response("approve_release", confirmed=True))
