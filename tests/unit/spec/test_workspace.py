"""Behavioral coverage for the Spec command workspace."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError, CommandWorkspaceHost
from attune.mcp.server import AttuneMCPServer
from attune.spec.state import SpecState, save_state
from attune.spec.workspace import (
    SpecArtifactReceipt,
    SpecLifecycleReceipt,
    SpecTaskGateReceipt,
    SpecWorkspaceAdapter,
    SpecWorkspaceState,
)

_PLAN = """# Demo plan

<task id="1" name="first"><objective>First task</objective></task>
<task id="2" name="second"><objective>Second task</objective></task>
"""


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "attune" / "alpha").mkdir(parents=True)
    (repo / "src" / "attune" / "alpha" / "__init__.py").write_text("")
    (repo / "src" / "attune" / "beta").mkdir()
    (repo / "src" / "attune" / "beta" / "__init__.py").write_text("")
    (repo / "docs" / "specs" / "existing-spec").mkdir(parents=True)
    (repo / ".claude" / "plans").mkdir(parents=True)
    (repo / ".git").mkdir()
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(repo))
    return host


def _intake() -> dict[str, object]:
    return {
        "route": "new",
        "outcome": "A renderer-backed spec flow exists.",
        "done_when": "Both tasks have approved receipts.",
        "area": "src/attune/alpha",
        "slug": "existing-spec",
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


def _response(action: str, *, confirmed: bool = False) -> WorkspaceActionResponse:
    return WorkspaceActionResponse(WorkspaceViewId.EXECUTION, action, confirmed)


def _artifacts() -> dict[str, object]:
    return {
        "kind": "artifacts_created",
        "plan_path": ".claude/plans/demo.md",
        "artifacts": [
            {"path": ".claude/plans/demo.md", "kind": "plan"},
            {"path": "docs/specs/demo/requirements.md", "kind": "requirements"},
            {"path": "docs/specs/demo/tasks.md", "kind": "tasks"},
        ],
        "task_ids": ["1", "2"],
        "probes": ["pytest tests/unit/spec/test_workspace.py -q"],
    }


def _gate(boundary: str, state: str = "PASS") -> dict[str, object]:
    return {
        "kind": "lifecycle_gate",
        "boundary": boundary,
        "receipts": [
            {
                "gate_id": "symbol-reality",
                "boundary": boundary,
                "state": state,
                "detail": f"{boundary} {state.lower()} receipt",
            }
        ],
    }


async def _to_review(host: CommandWorkspaceHost):
    preview = await host.open("spec", _intake())
    creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
    gate = await host.publish(creating.record.workspace_id, _artifacts())
    return await host.publish(gate.record.workspace_id, _gate("tasks"))


async def _to_execution(host: CommandWorkspaceHost):
    review = await _to_review(host)
    approval = await host.collect(_payload(review, "approve_plan"))
    gate = await host.collect(_payload(approval, "start_execution", confirmed=True))
    return await host.publish(gate.record.workspace_id, _gate("execution"))


@pytest.mark.asyncio
async def test_new_spec_preview_reuses_tree_derived_intake_and_collision_warning(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    preview = await _host(repo).open("spec", _intake())

    state = preview.record.state
    assert state.area_options == ("src/attune/alpha", "src/attune/beta")
    assert state.taken_slugs == ("existing-spec",)
    assert "already exists" in state.contract
    assert "tree-derived area" in preview.markdown
    assert "create_spec" in preview.html
    assert "`create_spec`" in preview.markdown


@pytest.mark.asyncio
async def test_creation_review_redo_and_artifact_receipt_are_canonical(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    preview = await host.open("spec", _intake())
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(preview, "create_spec"))
    creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
    assert creating.result["delegate"] == "spec.create"
    gate = await host.publish(creating.record.workspace_id, _artifacts())
    assert gate.result == {"delegate": "spec.lifecycle_gate", "boundary": "tasks"}
    review = await host.publish(gate.record.workspace_id, _gate("tasks"))
    assert review.record.state.stage == "review"
    assert ".claude/plans/demo.md" in review.render.markdown
    redo = await host.collect(_payload(review, "redo_plan"))
    assert redo.record.state.stage == "creating"
    assert redo.result["delegate"] == "spec.redo"


@pytest.mark.asyncio
async def test_chair_required_is_bound_and_blocked_cannot_be_acknowledged(
    tmp_path: Path,
) -> None:
    host = _host(_repo(tmp_path))
    preview = await host.open("spec", _intake())
    creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
    gate = await host.publish(creating.record.workspace_id, _artifacts())
    chair = await host.publish(gate.record.workspace_id, _gate("tasks", "CHAIR_REQUIRED"))
    assert chair.record.state.stage == "chair_required"
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(chair, "acknowledge_gate"))
    review = await host.collect(_payload(chair, "acknowledge_gate", confirmed=True))
    assert review.record.state.stage == "review"

    approval = await host.collect(_payload(review, "approve_plan"))
    running_gate = await host.collect(_payload(approval, "start_execution", confirmed=True))
    blocked = await host.publish(
        running_gate.record.workspace_id,
        _gate("execution", "BLOCKED"),
    )
    assert blocked.record.state.stage == "blocked"
    assert [action.id for action in blocked.record.view.actions] == ["retry_gate"]
    with pytest.raises(CommandWorkspaceError, match="not allowed"):
        await host.collect(_payload(blocked, "acknowledge_gate", confirmed=True))
    rerun = await host.collect(_payload(blocked, "retry_gate"))
    executing = await host.publish(rerun.record.workspace_id, _gate("execution"))
    assert executing.record.state.stage == "executing"


@pytest.mark.asyncio
async def test_task_gates_progress_auto_run_and_terminal_artifact_receipt(
    tmp_path: Path,
) -> None:
    host = _host(_repo(tmp_path))
    executing = await _to_execution(host)
    started = await host.publish(
        executing.record.workspace_id,
        {"kind": "task_started", "task_id": "1"},
    )
    progress = await host.publish(
        started.record.workspace_id,
        {"kind": "execution_progress", "detail": "tests running"},
    )
    assert progress.record.revision == started.record.revision
    assert progress.record.event_sequence == started.record.event_sequence + 1
    assert "tests running" in progress.render.markdown
    gate = await host.publish(
        progress.record.workspace_id,
        {
            "kind": "task_result",
            "task_id": "1",
            "severity": "medium",
            "score": 86,
            "probes": ["pytest task-one -q"],
            "detail": "quality gates passed",
        },
    )
    auto = await host.collect(_payload(gate, "auto_run_remaining", confirmed=True))
    assert auto.record.state.completed == ("1",)
    assert auto.record.state.auto_run is True
    assert auto.result["save_state"]["completed"] == ["1"]

    started = await host.publish(
        auto.record.workspace_id,
        {"kind": "task_started", "task_id": "2"},
    )
    terminal = await host.publish(
        started.record.workspace_id,
        {
            "kind": "task_result",
            "task_id": "2",
            "severity": "low",
            "score": 99,
            "probes": ["pytest task-two -q"],
            "detail": "clean",
        },
    )
    assert terminal.record.terminal is True
    assert terminal.record.state.completed == ("1", "2")
    assert terminal.result["disposition"] == "auto"
    assert ".claude/plans/demo.md" in terminal.render.markdown
    assert "pytest tests/unit/spec/test\\_workspace.py -q" in terminal.render.markdown


@pytest.mark.asyncio
async def test_high_severity_interrupts_auto_run_and_requires_explicit_risk_ack(
    tmp_path: Path,
) -> None:
    host = _host(_repo(tmp_path))
    executing = await _to_execution(host)
    started = await host.publish(
        executing.record.workspace_id,
        {"kind": "task_started", "task_id": "1"},
    )
    first_gate = await host.publish(
        started.record.workspace_id,
        {
            "kind": "task_result",
            "task_id": "1",
            "severity": "low",
            "score": 99,
            "probes": ["pytest first -q"],
            "detail": "clean",
        },
    )
    auto = await host.collect(_payload(first_gate, "auto_run_remaining", confirmed=True))
    started = await host.publish(
        auto.record.workspace_id,
        {"kind": "task_started", "task_id": "2"},
    )
    gate = await host.publish(
        started.record.workspace_id,
        {
            "kind": "task_result",
            "task_id": "2",
            "severity": "high",
            "score": 20,
            "probes": ["pytest failing -q"],
            "detail": "security gate failed",
        },
    )
    assert gate.record.state.stage == "task_gate"
    assert [action.id for action in gate.record.view.actions] == [
        "fix_retry",
        "acknowledge_risk",
    ]
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        await host.collect(_payload(gate, "acknowledge_risk"))
    continued = await host.collect(_payload(gate, "acknowledge_risk", confirmed=True))
    assert continued.record.state.completed == ("1", "2")
    assert continued.record.terminal is True


@pytest.mark.asyncio
async def test_resume_reads_real_xml_tasks_and_persisted_progress(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    plan = repo / ".claude" / "plans" / "demo.md"
    plan.write_text(_PLAN)
    save_state(
        SpecState(
            plan_path=str(plan),
            completed=["1"],
            current="2",
            auto_run=True,
        )
    )
    resumed = await _host(repo).open(
        "spec",
        {"route": "resume", "plan_path": ".claude/plans/demo.md"},
    )

    state = resumed.record.state
    assert state.task_ids == ("1", "2")
    assert state.completed == ("1",)
    assert state.current == "2"
    assert state.auto_run is True
    assert state.area_options == ("src/attune/alpha", "src/attune/beta")
    assert ".claude/plans/demo.md" in resumed.markdown


@pytest.mark.asyncio
async def test_generic_server_registers_spec_adapter(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with (
        patch.object(AttuneMCPServer, "_register_plugin_tools"),
        patch("attune.mcp.version_check.check_for_updates", return_value=None),
    ):
        server = AttuneMCPServer(workspace_root=str(repo))
    opened = await server.call_tool(
        "command_workspace_open",
        {"adapter_id": "spec", "intake": _intake()},
    )
    assert opened["success"] is True
    assert opened["adapter_id"] == "spec"
    assert "src/attune/alpha" in opened["markdown"]


def test_value_objects_and_state_reject_invalid_authority() -> None:
    with pytest.raises(CommandWorkspaceError, match="project-relative"):
        SpecArtifactReceipt("../escape", "plan")
    with pytest.raises(CommandWorkspaceError, match="kind"):
        SpecArtifactReceipt("plan.md", "")
    with pytest.raises(CommandWorkspaceError, match="boundary"):
        SpecLifecycleReceipt("g", "design", "PASS", "ok")
    with pytest.raises(CommandWorkspaceError, match="state"):
        SpecLifecycleReceipt("g", "tasks", "MAYBE", "ok")
    with pytest.raises(CommandWorkspaceError, match="severity"):
        SpecTaskGateReceipt("1", "critical", 10, ("pytest",), "bad")
    with pytest.raises(CommandWorkspaceError, match="between 0 and 100"):
        SpecTaskGateReceipt("1", "high", 101, ("pytest",), "bad")
    with pytest.raises(CommandWorkspaceError, match="current task cannot"):
        SpecWorkspaceState(
            outcome="x",
            done_when="y",
            area="a",
            slug="demo",
            contract="c",
            area_options=(),
            taken_slugs=(),
            task_ids=("1",),
            completed=("1",),
            current="1",
        )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: SpecLifecycleReceipt("", "tasks", "PASS", "ok"), "gate_id"),
        (lambda: SpecLifecycleReceipt("g", "tasks", "PASS", ""), "detail"),
        (lambda: SpecTaskGateReceipt("", "low", 90, ("p",), "ok"), "task_id"),
        (lambda: SpecTaskGateReceipt("1", "low", True, ("p",), "ok"), "numeric"),
        (lambda: SpecTaskGateReceipt("1", "low", 90, (), "ok"), "exact probes"),
        (lambda: SpecTaskGateReceipt("1", "low", 90, ("p",), ""), "detail"),
    ],
)
def test_receipt_field_validation(factory, message: str) -> None:
    with pytest.raises(CommandWorkspaceError, match=message):
        factory()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"outcome": ""}, "outcome"),
        ({"done_when": ""}, "done_when"),
        ({"slug": "Not a Slug"}, "kebab-case"),
        ({"stage": "missing"}, "stage"),
        ({"task_ids": ("1", "1")}, "task ids must be unique"),
        ({"completed": ("1",)}, "completed ids"),
        ({"current": "1"}, "current task must belong"),
        ({"gate_boundary": "design"}, "gate boundary"),
        ({"gate_next_stage": "missing"}, "successor stage"),
        (
            {
                "artifacts": (
                    SpecArtifactReceipt("plan.md", "plan"),
                    SpecArtifactReceipt("plan.md", "tasks"),
                )
            },
            "artifact paths must be unique",
        ),
    ],
)
def test_workspace_state_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "outcome": "x",
        "done_when": "y",
        "area": "a",
        "slug": "demo",
        "contract": "c",
        "area_options": (),
        "taken_slugs": (),
    }
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        SpecWorkspaceState(**values)


@pytest.mark.asyncio
async def test_edit_replacement_and_approval_redo_paths(tmp_path: Path) -> None:
    host = _host(_repo(tmp_path))
    preview = await host.open("spec", _intake())
    intake = await host.collect(_payload(preview, "edit_spec"))
    assert intake.record.state.stage == "intake"
    revised = _intake()
    revised["outcome"] = "Revised"
    preview = await host.open("spec", revised, workspace_id=preview.record.workspace_id)
    assert preview.record.state.outcome == "Revised"
    review = await _to_review(host)
    approval = await host.collect(_payload(review, "approve_plan"))
    redo = await host.collect(_payload(approval, "redo_plan"))
    assert redo.record.state.stage == "creating"


def test_adapter_create_validation(tmp_path: Path) -> None:
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    with pytest.raises(CommandWorkspaceError, match="select edit_spec"):
        adapter.create(_intake(), prior_state=preview)
    intake = replace(preview, stage="intake")
    with pytest.raises(CommandWorkspaceError, match="resume cannot replace"):
        adapter.create(
            {"route": "resume", "plan_path": ".claude/plans/demo.md"},
            prior_state=intake,
        )
    with pytest.raises(CommandWorkspaceError, match="route must be"):
        adapter.create({**_intake(), "route": "import"})
    with pytest.raises(CommandWorkspaceError, match="unknown Spec intake"):
        adapter.create({**_intake(), "extra": True})


def test_artifact_and_lifecycle_event_validation(tmp_path: Path) -> None:
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    creating = adapter.apply(preview, _response("create_spec", confirmed=True)).state
    with pytest.raises(CommandWorkspaceError, match="creation stage"):
        adapter.publish(preview, _artifacts())
    for artifacts in ("bad", [], [1]):
        event = {**_artifacts(), "artifacts": artifacts}
        with pytest.raises(CommandWorkspaceError, match="artifacts"):
            adapter.publish(creating, event)
    for field, value, message in (
        ("task_ids", "1", "must be a list"),
        ("task_ids", [], "non-empty"),
        ("task_ids", ["1", "1"], "unique"),
        ("probes", [""], "non-empty"),
        ("plan_path", "other.md", "received artifact"),
    ):
        with pytest.raises(CommandWorkspaceError, match=message):
            adapter.publish(creating, {**_artifacts(), field: value})

    gate = adapter.publish(creating, _artifacts()).state
    with pytest.raises(CommandWorkspaceError, match="gate-running stage"):
        adapter.publish(preview, _gate("tasks"))
    with pytest.raises(CommandWorkspaceError, match="does not match"):
        adapter.publish(gate, _gate("execution"))
    for receipts in ("bad", [], [1]):
        with pytest.raises(CommandWorkspaceError, match="lifecycle receipts"):
            adapter.publish(gate, {**_gate("tasks"), "receipts": receipts})
    revised = adapter.publish(gate, _gate("tasks", "REVISE"))
    assert revised.state.stage == "blocked"


def test_task_event_and_decision_validation(tmp_path: Path) -> None:
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    executing = SpecWorkspaceState(
        outcome="x",
        done_when="y",
        area="a",
        slug="demo",
        contract="c",
        area_options=(),
        taken_slugs=(),
        stage="executing",
        plan_path="plan.md",
        task_ids=("1", "2"),
    )
    with pytest.raises(CommandWorkspaceError, match="execution stage"):
        adapter.publish(
            replace(executing, stage="review"), {"kind": "task_started", "task_id": "1"}
        )
    with pytest.raises(CommandWorkspaceError, match="pending task"):
        adapter.publish(executing, {"kind": "task_started", "task_id": "3"})
    with pytest.raises(CommandWorkspaceError, match="plan order"):
        adapter.publish(executing, {"kind": "task_started", "task_id": "2"})
    with pytest.raises(CommandWorkspaceError, match="current execution task"):
        adapter.publish(executing, {"kind": "task_result", "task_id": "1"})
    current = adapter.publish(executing, {"kind": "task_started", "task_id": "1"}).state
    with pytest.raises(CommandWorkspaceError, match="does not match current"):
        adapter.publish(current, {"kind": "task_result", "task_id": "2"})
    with pytest.raises(CommandWorkspaceError, match="task probes must be a list"):
        adapter.publish(
            current,
            {"kind": "task_result", "task_id": "1", "probes": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="execution stage"):
        adapter.publish(
            replace(executing, stage="review"),
            {"kind": "execution_progress", "detail": "x"},
        )

    low_receipt = SpecTaskGateReceipt("1", "low", 90, ("pytest",), "ok")
    low_gate = replace(current, stage="task_gate", task_receipt=low_receipt)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(low_gate, _response("fix_retry"))
    redo = adapter.apply(low_gate, _response("redo_task"))
    assert redo.result["delegate"] == "spec.retry_task"
    empty_gate = replace(low_gate, task_receipt=None)
    with pytest.raises(CommandWorkspaceError, match="no current receipt"):
        adapter.apply(empty_gate, _response("approve_task"))

    high_receipt = SpecTaskGateReceipt("1", "high", 10, ("pytest",), "bad")
    high_gate = replace(current, stage="task_gate", task_receipt=high_receipt)
    fixed = adapter.apply(high_gate, _response("fix_retry"))
    assert fixed.result["task_id"] == "1"
    with pytest.raises(CommandWorkspaceError, match="explicit confirmation"):
        adapter.apply(high_gate, _response("acknowledge_risk"))


def test_resume_validation_and_completed_plan_rejection(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    adapter = SpecWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="unknown Spec resume"):
        adapter.create({"route": "resume", "plan_path": "x.md", "extra": True})
    for path in ("", "/absolute.md", "../escape.md"):
        with pytest.raises(CommandWorkspaceError, match="project-relative"):
            adapter.create({"route": "resume", "plan_path": path})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"route": "resume", "plan_path": "missing.md"})
    empty = repo / ".claude" / "plans" / "empty.md"
    empty.write_text("# No tasks\n")
    with pytest.raises(CommandWorkspaceError, match="no XML tasks"):
        adapter.create({"route": "resume", "plan_path": ".claude/plans/empty.md"})
    plan = repo / ".claude" / "plans" / "done.md"
    plan.write_text(_PLAN)
    save_state(SpecState(plan_path=str(plan), completed=["1", "2"]))
    with pytest.raises(CommandWorkspaceError, match="already complete"):
        adapter.create({"route": "resume", "plan_path": ".claude/plans/done.md"})


def test_direct_adapter_rejects_incompatible_and_illegal_transitions(tmp_path: Path) -> None:
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    for method, args in (
        (adapter.project, (object(),)),
        (adapter.apply, (object(), _response("x"))),
        (adapter.publish, (object(), {"kind": "x"})),
    ):
        with pytest.raises(CommandWorkspaceError, match="incompatible state"):
            method(*args)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, _response("approve_plan"))
    with pytest.raises(CommandWorkspaceError, match="unknown Spec event"):
        adapter.publish(preview, {"kind": "missing"})
