"""Characterize the current fixed Roundtable roster and its workspace gate."""

from __future__ import annotations

import pytest
from attune_forms import WorkspaceActionResponse, WorkspaceViewId

from attune.elicitation.command_workspace import CommandWorkspaceError
from attune.roundtable.rotation import CANONICAL_SEATS
from attune.roundtable.routine import PLAN_ONLY_SEATS, SEAT_RECIPES
from attune.roundtable.workspace import RoundtableWorkspaceAdapter, RoundtableWorkspaceState

_EXPECTED_SEATS = ("claude", "antigravity", "codex")
_EXPECTED_RECIPES = (
    ("claude", ("claude", "-p", "{brief}")),
    ("antigravity", ("agy", "--add-dir", ".", "-p", "{brief}", "--mode", "plan")),
    ("codex", ("codex", "exec", "--skip-git-repo-check", "-")),
)


def _state(*, max_invocations: int = 9, stage: str = "running") -> RoundtableWorkspaceState:
    return RoundtableWorkspaceState(
        question="Should all commands use the shared renderer?",
        thread_id="roster-characterization",
        expected_rounds=3,
        max_invocations=max_invocations,
        stage=stage,
    )


def _receipts(seats: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        {
            "seat": seat,
            "status": "complete",
            "message_id": index,
            "detail": f"{seat} completed round 1",
            "compiler_clean": True,
        }
        for index, seat in enumerate(seats, start=1)
    ]


def test_fixed_roster_constants_and_recipes_are_exact() -> None:
    assert CANONICAL_SEATS == _EXPECTED_SEATS
    assert SEAT_RECIPES == _EXPECTED_RECIPES
    assert PLAN_ONLY_SEATS == frozenset({"antigravity"})
    assert tuple(seat for seat, _ in SEAT_RECIPES) == CANONICAL_SEATS


def test_start_refuses_an_invocation_cap_smaller_than_the_fixed_roster() -> None:
    action = WorkspaceActionResponse(
        WorkspaceViewId.PREVIEW,
        "start_roundtable",
        True,
    )

    with pytest.raises(CommandWorkspaceError) as caught:
        RoundtableWorkspaceAdapter().apply(
            _state(max_invocations=2, stage="preview"),
            action,
        )

    assert caught.value.problems == ["Roundtable invocation cap cannot cover the fixed roster"]


def test_round_complete_accepts_the_exact_roster_in_submitted_order() -> None:
    submitted = ("codex", "claude", "antigravity")

    transition = RoundtableWorkspaceAdapter().publish(
        _state(),
        {"kind": "round_complete", "receipts": _receipts(submitted)},
    )

    assert isinstance(transition.state, RoundtableWorkspaceState)
    assert transition.state.stage == "checkpoint"
    assert tuple(receipt.seat for receipt in transition.state.seat_receipts) == submitted


@pytest.mark.parametrize(
    ("submitted", "problem"),
    (
        (
            ("claude", "antigravity"),
            "round_complete requires exactly the fixed Roundtable roster",
        ),
        (
            ("claude", "antigravity", "codex", "claude"),
            "Roundtable state may retain one receipt per seat",
        ),
        (
            ("claude", "antigravity", "foreign"),
            "unknown Roundtable seat 'foreign'",
        ),
    ),
)
def test_round_complete_refusal_messages_are_exact(
    submitted: tuple[str, ...],
    problem: str,
) -> None:
    with pytest.raises(CommandWorkspaceError) as caught:
        RoundtableWorkspaceAdapter().publish(
            _state(),
            {"kind": "round_complete", "receipts": _receipts(submitted)},
        )

    assert caught.value.problems == [problem]
