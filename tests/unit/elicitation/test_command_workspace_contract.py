"""Reference contract for the shared command-workspace extraction.

The production seam is intentionally absent in Task 1. These tests keep the
renderer as data-only infrastructure and use three small fake adapters to pin
the minimum attune-ai boundary: create domain state, project one view, and
apply one collected action. Legal actions, confirmation policy, loops, and
terminal receipts are adapter-issued; the host never infers them from a view
name.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pytest
from attune_forms import (
    WorkspaceActionBinding,
    WorkspaceValidationError,
    WorkspaceView,
    collect_workspace_action,
    workspace_from_dict,
)

from attune.elicitation.command_workspace import CommandWorkspaceAdapter


@dataclass(frozen=True)
class _Transition:
    state: object
    terminal: bool = False


@runtime_checkable
class _CommandWorkspaceAdapter(Protocol):
    """Smallest command-owned seam exercised by all three shapes."""

    adapter_id: str
    schema_version: int

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> object: ...

    def project(self, state: object) -> WorkspaceView: ...

    def apply(self, state: object, action: str) -> _Transition: ...


@dataclass(frozen=True)
class _ScenarioAdapter:
    adapter_id: str
    initial_state: str
    views: Mapping[str, dict[str, object]]
    transitions: Mapping[tuple[str, str], _Transition]
    schema_version: int = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> object:
        return intake.get("resume_from", prior_state or self.initial_state)

    def project(self, state: object) -> WorkspaceView:
        return workspace_from_dict(self.views[str(state)])

    def apply(self, state: object, action: str) -> _Transition:
        return self.transitions[(str(state), action)]


@dataclass
class _ReferenceHost:
    """Test-only authority harness; Task 2 replaces this with production."""

    adapter: _CommandWorkspaceAdapter
    workspace_id: str
    state: object
    revision: int = 0
    terminal: bool = False

    @classmethod
    def start(
        cls,
        adapter: _CommandWorkspaceAdapter,
        intake: Mapping[str, object] | None = None,
    ) -> _ReferenceHost:
        return cls(
            adapter=adapter,
            workspace_id=f"workspace-{adapter.adapter_id}",
            state=adapter.create(intake or {}),
        )

    @property
    def view(self) -> WorkspaceView:
        return self.adapter.project(self.state)

    @property
    def binding(self) -> WorkspaceActionBinding:
        material = (
            f"{self.adapter.adapter_id}:{self.adapter.schema_version}:"
            f"{self.state!r}:{self.view!r}"
        )
        return WorkspaceActionBinding(
            workspace_id=self.workspace_id,
            revision=self.revision,
            action_nonce=f"nonce-{self.revision:011d}",
            contract_hash=hashlib.sha256(material.encode()).hexdigest(),
        )

    def collect(self, payload: Mapping[str, object]) -> _Transition:
        response = collect_workspace_action(self.view, payload, self.binding)
        transition = self.adapter.apply(self.state, response.action)
        self.state = transition.state
        self.terminal = transition.terminal
        self.revision += 1
        return transition


def _view(
    view_id: str,
    title: str,
    *actions: tuple[str, bool],
) -> dict[str, object]:
    return {
        "id": view_id,
        "title": title,
        "actions": [
            {
                "id": action_id,
                "label": action_id.replace("_", " ").title(),
                "consequence": "Authorize this exact checkpoint." if explicit else "",
                "requires_explicit_choice": explicit,
            }
            for action_id, explicit in actions
        ],
    }


def _payload(
    host: _ReferenceHost,
    action: str,
    *,
    confirmed: bool = False,
    binding: WorkspaceActionBinding | None = None,
) -> dict[str, object]:
    issued = binding or host.binding
    return {
        "__elicitation_response__": True,
        "title": host.view.title,
        "view": host.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **issued.to_payload(),
    }


def _fix_adapter() -> _ScenarioAdapter:
    return _ScenarioAdapter(
        adapter_id="fix",
        initial_state="preview",
        views={
            "preview": _view(
                "preview",
                "Fix workspace",
                ("edit_contract", False),
                ("run_fix", True),
            ),
            "intake": _view("intake", "Fix workspace", ("preview_contract", False)),
            "receipt": _view("receipt", "Fix workspace"),
        },
        transitions={
            ("preview", "edit_contract"): _Transition("intake"),
            ("preview", "run_fix"): _Transition("receipt", terminal=True),
            ("intake", "preview_contract"): _Transition("preview"),
        },
    )


def _roundtable_adapter() -> _ScenarioAdapter:
    return _ScenarioAdapter(
        adapter_id="roundtable",
        initial_state="round-1",
        views={
            "round-1": _view(
                "execution",
                "Roundtable workspace",
                ("advance_round", False),
                ("synthesize", False),
            ),
            "round-2": _view(
                "execution",
                "Roundtable workspace",
                ("advance_round", False),
                ("open_promotion", False),
            ),
            "promotion": _view(
                "execution",
                "Roundtable workspace",
                ("promote_batch", True),
                ("finish", True),
            ),
            "receipt": _view("receipt", "Roundtable workspace"),
        },
        transitions={
            ("round-1", "advance_round"): _Transition("round-2"),
            ("round-1", "synthesize"): _Transition("promotion"),
            ("round-2", "advance_round"): _Transition("round-2"),
            ("round-2", "open_promotion"): _Transition("promotion"),
            ("promotion", "promote_batch"): _Transition("promotion"),
            ("promotion", "finish"): _Transition("receipt", terminal=True),
        },
    )


def _spec_adapter() -> _ScenarioAdapter:
    return _ScenarioAdapter(
        adapter_id="spec",
        initial_state="task-review",
        views={
            "task-review": _view(
                "execution",
                "Spec workspace",
                ("redo_task", False),
                ("approve_task", True),
            ),
            "task-redo": _view(
                "execution",
                "Spec workspace",
                ("resubmit_task", False),
            ),
            "task-review-again": _view(
                "execution",
                "Spec workspace",
                ("redo_task", False),
                ("approve_task", True),
            ),
            "receipt": _view("receipt", "Spec workspace"),
        },
        transitions={
            ("task-review", "redo_task"): _Transition("task-redo"),
            ("task-redo", "resubmit_task"): _Transition("task-review-again"),
            ("task-review-again", "redo_task"): _Transition("task-redo"),
            ("task-review", "approve_task"): _Transition("receipt", terminal=True),
            ("task-review-again", "approve_task"): _Transition(
                "receipt",
                terminal=True,
            ),
        },
    )


@pytest.mark.parametrize(
    "adapter",
    [_fix_adapter(), _roundtable_adapter(), _spec_adapter()],
    ids=["fix", "nested-roundtable", "iterative-spec"],
)
def test_three_command_shapes_fit_the_same_three_method_boundary(
    adapter: _ScenarioAdapter,
) -> None:
    assert isinstance(adapter, _CommandWorkspaceAdapter)

    host = _ReferenceHost.start(adapter)

    assert isinstance(host.view, WorkspaceView)
    assert not {
        "round",
        "seat",
        "dissent",
        "requirement",
        "task_approval",
        "release_gate",
    }.intersection(vars(host))


def test_phase_names_do_not_imply_transitions_or_legal_actions() -> None:
    fix = _ReferenceHost.start(_fix_adapter())
    fix.collect(_payload(fix, "edit_contract"))
    assert fix.view.id.value == "intake"

    roundtable = _ReferenceHost.start(_roundtable_adapter())
    first_actions = {action.id for action in roundtable.view.actions}
    roundtable.collect(_payload(roundtable, "advance_round"))
    second_actions = {action.id for action in roundtable.view.actions}
    assert roundtable.view.id.value == "execution"
    assert first_actions != second_actions

    spec = _ReferenceHost.start(_spec_adapter())
    spec.collect(_payload(spec, "redo_task"))
    assert spec.view.id.value == "execution"
    assert {action.id for action in spec.view.actions} == {"resubmit_task"}


def test_nested_roundtable_checkpoint_rejects_stale_authority() -> None:
    host = _ReferenceHost.start(_roundtable_adapter())
    stale_binding = host.binding
    stale = _payload(host, "advance_round", binding=stale_binding)
    host.collect(stale)
    assert host.revision == 1

    with pytest.raises(WorkspaceValidationError, match="revision does not match"):
        host.collect(stale)

    assert host.revision == 1
    assert host.state == "round-2"


def test_iterative_spec_checkpoint_reissues_authority_and_confirmation() -> None:
    host = _ReferenceHost.start(_spec_adapter())
    first_review = host.binding
    host.collect(_payload(host, "redo_task", binding=first_review))
    host.collect(_payload(host, "resubmit_task"))
    assert host.state == "task-review-again"
    assert host.revision == 2

    with pytest.raises(WorkspaceValidationError, match="revision does not match"):
        host.collect(_payload(host, "redo_task", binding=first_review))
    with pytest.raises(WorkspaceValidationError, match="explicit confirmation"):
        host.collect(_payload(host, "approve_task"))

    host.collect(_payload(host, "approve_task", confirmed=True))
    assert host.terminal is True
    assert host.view.id.value == "receipt"
    assert host.revision == 3


def test_confirmation_policy_is_adapter_issued_not_phase_implied() -> None:
    fix = _ReferenceHost.start(_fix_adapter())
    with pytest.raises(WorkspaceValidationError, match="explicit confirmation"):
        fix.collect(_payload(fix, "run_fix"))
    assert fix.revision == 0

    roundtable = _ReferenceHost.start(_roundtable_adapter())
    roundtable.collect(_payload(roundtable, "advance_round"))
    assert roundtable.revision == 1


def test_production_protocol_closes_the_named_extraction_gap() -> None:
    assert {"create", "project", "apply"}.issubset(CommandWorkspaceAdapter.__dict__)
    assert isinstance(_fix_adapter(), CommandWorkspaceAdapter)
