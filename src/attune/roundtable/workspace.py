"""Shared-renderer adapter for moderated Roundtable sessions."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)
from attune.roundtable.rotation import CANONICAL_SEATS

_THREAD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_STAGES = frozenset(
    {"preview", "intake", "running", "checkpoint", "synthesizing", "triage", "receipt"}
)
_DISPOSITIONS = frozenset({"promote", "decline", "another_round"})


@dataclass(frozen=True)
class RoundtableSeatReceipt:
    """One moderator-validated seat result already recorded on the board."""

    seat: str
    status: str
    round_number: int
    message_id: int | None = None
    detail: str = ""
    compiler_clean: bool = True

    def __post_init__(self) -> None:
        if self.seat not in CANONICAL_SEATS:
            raise CommandWorkspaceError([f"unknown Roundtable seat {self.seat!r}"])
        if self.status not in {"pending", "running", "complete", "absent", "failed"}:
            raise CommandWorkspaceError([f"invalid seat status {self.status!r}"])
        if self.round_number < 1 or self.round_number > 3:
            raise CommandWorkspaceError(["Roundtable receipt round must be 1..3"])
        if self.message_id is not None and self.message_id < 1:
            raise CommandWorkspaceError(["Roundtable board message id must be positive"])
        if not self.compiler_clean:
            raise CommandWorkspaceError(
                [f"compiler-dirty output from {self.seat} cannot enter workspace state"]
            )


@dataclass(frozen=True)
class RoundtableCandidate:
    """One chair-rulable promotion candidate."""

    message_id: int
    title: str
    detail: str

    def __post_init__(self) -> None:
        if self.message_id < 1:
            raise CommandWorkspaceError(["promotion candidate message id must be positive"])
        if not self.title.strip() or not self.detail.strip():
            raise CommandWorkspaceError(["promotion candidate requires title and detail"])


@dataclass(frozen=True)
class RoundtableRuling:
    """One per-item chair disposition."""

    message_id: int
    disposition: str

    def __post_init__(self) -> None:
        if self.message_id < 1:
            raise CommandWorkspaceError(["Roundtable ruling message id must be positive"])
        if self.disposition not in _DISPOSITIONS:
            raise CommandWorkspaceError(["invalid Roundtable ruling disposition"])


@dataclass(frozen=True)
class RoundtableWorkspaceState:
    """Roundtable-owned canonical state; the shared host treats it as opaque."""

    question: str
    thread_id: str
    expected_rounds: int
    max_invocations: int
    stage: str = "preview"
    round_number: int = 1
    seat_receipts: tuple[RoundtableSeatReceipt, ...] = ()
    followups: tuple[str, ...] = ()
    synthesis: str = ""
    candidates: tuple[RoundtableCandidate, ...] = ()
    triage_index: int = 0
    rulings: tuple[RoundtableRuling, ...] = ()
    halt_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "seat_receipts", tuple(self.seat_receipts))
        object.__setattr__(self, "followups", tuple(self.followups))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "rulings", tuple(self.rulings))
        problems: list[str] = []
        if not self.question.strip():
            problems.append("Roundtable question must not be empty")
        if not _THREAD_RE.fullmatch(self.thread_id):
            problems.append("Roundtable thread_id is invalid")
        if self.expected_rounds < 1 or self.expected_rounds > 3:
            problems.append("Roundtable expected_rounds must be 1..3")
        if self.max_invocations < 1:
            problems.append("Roundtable max_invocations must be positive")
        if self.stage not in _STAGES:
            problems.append("Roundtable workspace stage is invalid")
        if self.round_number < 1 or self.round_number > 3:
            problems.append("Roundtable round_number must be 1..3")
        if len(self.candidates) > 7:
            problems.append("Roundtable workspace supports at most 7 active candidates")
        if self.triage_index < 0 or self.triage_index > len(self.candidates):
            problems.append("Roundtable triage_index is out of range")
        candidate_ids = [candidate.message_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            problems.append("Roundtable promotion candidate ids must be unique")
        ruling_ids = [ruling.message_id for ruling in self.rulings]
        if len(ruling_ids) != len(set(ruling_ids)):
            problems.append("Roundtable candidate may be ruled only once")
        receipt_seats = [receipt.seat for receipt in self.seat_receipts]
        if len(receipt_seats) != len(set(receipt_seats)):
            problems.append("Roundtable state may retain one receipt per seat")
        if problems:
            raise CommandWorkspaceError(problems)

    @property
    def promoted_ids(self) -> tuple[int, ...]:
        """Return exactly the message ids the chair promoted."""
        return tuple(
            ruling.message_id for ruling in self.rulings if ruling.disposition == "promote"
        )


def _int_value(raw: object, name: str, *, default: int) -> int:
    value = default if raw is None else raw
    if isinstance(value, bool) or not isinstance(value, int):
        raise CommandWorkspaceError([f"Roundtable {name} must be an integer"])
    return value


def _receipt(raw: Mapping[str, object], round_number: int) -> RoundtableSeatReceipt:
    message_id = raw.get("message_id")
    if message_id is not None and (isinstance(message_id, bool) or not isinstance(message_id, int)):
        raise CommandWorkspaceError(["Roundtable seat message_id must be an integer"])
    return RoundtableSeatReceipt(
        seat=str(raw.get("seat", "")),
        status=str(raw.get("status", "")),
        round_number=round_number,
        message_id=message_id,
        detail=str(raw.get("detail", "")),
        compiler_clean=raw.get("compiler_clean", True) is True,
    )


def _candidate(raw: Mapping[str, object]) -> RoundtableCandidate:
    message_id = raw.get("message_id")
    if isinstance(message_id, bool) or not isinstance(message_id, int):
        raise CommandWorkspaceError(["promotion candidate message_id must be an integer"])
    return RoundtableCandidate(
        message_id=message_id,
        title=str(raw.get("title", "")),
        detail=str(raw.get("detail", "")),
    )


class RoundtableWorkspaceAdapter:
    """Roundtable lifecycle, rulings, and receipt semantics."""

    adapter_id = "roundtable"
    schema_version = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> RoundtableWorkspaceState:
        """Validate intake or replace an explicit edit state."""
        if prior_state is not None and (
            not isinstance(prior_state, RoundtableWorkspaceState) or prior_state.stage != "intake"
        ):
            raise CommandWorkspaceError(
                ["select edit_roundtable before replacing Roundtable intake"]
            )
        allowed = {"question", "thread_id", "expected_rounds", "max_invocations"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown Roundtable intake key {key!r}" for key in unknown]
            )
        return RoundtableWorkspaceState(
            question=str(intake.get("question", "")).strip(),
            thread_id=str(intake.get("thread_id", "")).strip(),
            expected_rounds=_int_value(
                intake.get("expected_rounds"),
                "expected_rounds",
                default=1,
            ),
            max_invocations=_int_value(
                intake.get("max_invocations"),
                "max_invocations",
                default=3,
            ),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Project the current Roundtable stage through attune-forms."""
        if not isinstance(state, RoundtableWorkspaceState):
            raise CommandWorkspaceError(["Roundtable adapter received incompatible state"])
        data = self._view_data(state)
        view = workspace_from_dict(data)
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "thread": state.thread_id,
            "stage": state.stage,
            "round": state.round_number,
            "candidate": (
                state.candidates[state.triage_index].message_id
                if state.stage == "triage" and state.triage_index < len(state.candidates)
                else None
            ),
            "actions": [action.id for action in view.actions],
        }
        digest = hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return CommandWorkspaceProjection(view, digest if view.actions else "")

    def apply(
        self,
        state: object,
        action: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        """Apply one chair/moderator action without invoking a seat."""
        if not isinstance(state, RoundtableWorkspaceState):
            raise CommandWorkspaceError(["Roundtable adapter received incompatible state"])
        if state.stage == "preview":
            if action.action == "edit_roundtable":
                return CommandWorkspaceTransition(replace(state, stage="intake"))
            if action.action == "start_roundtable":
                if state.max_invocations < len(CANONICAL_SEATS):
                    raise CommandWorkspaceError(
                        ["Roundtable invocation cap cannot cover the fixed roster"]
                    )
                return CommandWorkspaceTransition(
                    replace(state, stage="running"),
                    result={"delegate": "roundtable.run_round", "round": 1},
                )
        if state.stage == "checkpoint":
            if action.action == "next_round" and self._can_run_next_round(state):
                next_round = state.round_number + 1
                return CommandWorkspaceTransition(
                    replace(
                        state,
                        stage="running",
                        round_number=next_round,
                        seat_receipts=(),
                        followups=(),
                        halt_reason="",
                    ),
                    result={"delegate": "roundtable.run_round", "round": next_round},
                )
            if action.action == "synthesize":
                return CommandWorkspaceTransition(
                    replace(state, stage="synthesizing"),
                    result={"delegate": "roundtable.synthesize"},
                )
        if state.stage == "triage":
            return self._apply_triage(state, action)
        raise CommandWorkspaceError(
            [f"Roundtable action {action.action!r} is not legal in stage {state.stage!r}"]
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Apply one moderator/executor event after command-owned validation."""
        if not isinstance(state, RoundtableWorkspaceState):
            raise CommandWorkspaceError(["Roundtable adapter received incompatible state"])
        kind = event.get("kind")
        if kind == "seat_progress":
            return self._publish_seat_progress(state, event)
        if kind == "round_complete":
            return self._publish_round_complete(state, event)
        if kind == "synthesis":
            return self._publish_synthesis(state, event)
        raise CommandWorkspaceError([f"unknown Roundtable event {kind!r}"])

    @staticmethod
    def _publish_seat_progress(
        state: RoundtableWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage not in {"running", "synthesizing"}:
            raise CommandWorkspaceError(["seat progress requires an active Roundtable stage"])
        raw = event.get("receipt")
        if not isinstance(raw, Mapping):
            raise CommandWorkspaceError(["seat_progress requires a receipt mapping"])
        receipt = _receipt(raw, state.round_number)
        retained = tuple(item for item in state.seat_receipts if item.seat != receipt.seat)
        return CommandWorkspaceTransition(
            replace(state, seat_receipts=(*retained, receipt)),
            result={"seat": receipt.seat, "status": receipt.status},
            authority_changed=False,
        )

    @staticmethod
    def _publish_round_complete(
        state: RoundtableWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "running":
            raise CommandWorkspaceError(["round_complete requires a running round"])
        raw_receipts = event.get("receipts")
        if not isinstance(raw_receipts, Sequence) or isinstance(raw_receipts, str | bytes):
            raise CommandWorkspaceError(["round_complete requires receipt mappings"])
        receipts = tuple(
            _receipt(raw, state.round_number) for raw in raw_receipts if isinstance(raw, Mapping)
        )
        if len(receipts) != len(raw_receipts):
            raise CommandWorkspaceError(["round_complete receipt is not a mapping"])
        if {receipt.seat for receipt in receipts} != set(CANONICAL_SEATS):
            raise CommandWorkspaceError(
                ["round_complete requires exactly the fixed Roundtable roster"]
            )
        followups_raw = event.get("followups", ())
        if not isinstance(followups_raw, Sequence) or isinstance(followups_raw, str | bytes):
            raise CommandWorkspaceError(["Roundtable followups must be a list"])
        return CommandWorkspaceTransition(
            replace(
                state,
                stage="checkpoint",
                seat_receipts=receipts,
                followups=tuple(str(item) for item in followups_raw),
                halt_reason=str(event.get("halt_reason", "")),
            )
        )

    @staticmethod
    def _publish_synthesis(
        state: RoundtableWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "synthesizing":
            raise CommandWorkspaceError(["synthesis event requires synthesizing stage"])
        body = str(event.get("body", "")).strip()
        if not body:
            raise CommandWorkspaceError(["Roundtable synthesis must not be empty"])
        raw_candidates = event.get("candidates", ())
        if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, str | bytes):
            raise CommandWorkspaceError(["Roundtable candidates must be a list"])
        candidates = tuple(_candidate(raw) for raw in raw_candidates if isinstance(raw, Mapping))
        if len(candidates) != len(raw_candidates):
            raise CommandWorkspaceError(["Roundtable candidate is not a mapping"])
        terminal = not candidates
        successor = replace(
            state,
            stage="receipt" if terminal else "triage",
            synthesis=body,
            candidates=candidates,
            triage_index=0,
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=terminal,
            result={"candidate_count": len(candidates)},
        )

    def _apply_triage(
        self,
        state: RoundtableWorkspaceState,
        response: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        if state.triage_index >= len(state.candidates):
            raise CommandWorkspaceError(["Roundtable triage has no current candidate"])
        candidate = state.candidates[state.triage_index]
        if response.action not in _DISPOSITIONS:
            raise CommandWorkspaceError([f"unknown Roundtable disposition {response.action!r}"])
        if response.action == "promote" and not response.confirmed:
            raise CommandWorkspaceError(["promotion requires explicit chair confirmation"])
        ruling = RoundtableRuling(candidate.message_id, response.action)
        if response.action == "another_round":
            if not self._can_run_next_round(state):
                raise CommandWorkspaceError(["Roundtable round ceiling or invocation cap reached"])
            next_round = state.round_number + 1
            return CommandWorkspaceTransition(
                replace(
                    state,
                    stage="running",
                    round_number=next_round,
                    seat_receipts=(),
                    followups=(),
                    synthesis="",
                    candidates=(),
                    triage_index=0,
                    halt_reason="",
                ),
                result={
                    "delegate": "roundtable.run_round",
                    "round": next_round,
                    "ruling": response.action,
                    "message_id": candidate.message_id,
                },
            )
        next_index = state.triage_index + 1
        terminal = next_index == len(state.candidates)
        successor = replace(
            state,
            stage="receipt" if terminal else "triage",
            triage_index=next_index,
            rulings=(*state.rulings, ruling),
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=terminal,
            result={
                "ruling": response.action,
                "message_id": candidate.message_id,
                "remaining": len(state.candidates) - next_index,
            },
        )

    def _view_data(self, state: RoundtableWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            return {
                "id": "preview",
                "title": "Roundtable spend preview",
                "summary": "Review the fixed roster and bounded invocation plan.",
                "sections": [
                    {
                        "heading": "Plan",
                        "tone": "recommendation",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {"label": "Question", "value": state.question},
                                    {"label": "Thread", "value": state.thread_id},
                                    {
                                        "label": "Expected rounds",
                                        "value": str(state.expected_rounds),
                                    },
                                    {
                                        "label": "Invocation cap",
                                        "value": str(state.max_invocations),
                                    },
                                ],
                            },
                            {
                                "kind": "action_list",
                                "items": [{"label": seat} for seat in CANONICAL_SEATS],
                            },
                        ],
                    }
                ],
                "actions": [
                    {"id": "edit_roundtable", "label": "Edit plan"},
                    {
                        "id": "start_roundtable",
                        "label": "Start round table",
                        "consequence": "Authorize the fixed roster within the stated cap.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.stage == "intake":
            return {
                "id": "intake",
                "title": "Roundtable intake",
                "summary": "Submit revised intake to create a fresh preview.",
            }
        if state.stage in {"running", "synthesizing"}:
            items = [
                {
                    "label": receipt.seat,
                    "value": receipt.status,
                    "detail": receipt.detail,
                    "status": receipt.status,
                }
                for receipt in state.seat_receipts
            ] or [{"label": "Roster", "value": "awaiting seat receipts", "status": "running"}]
            return {
                "id": "execution",
                "title": "Roundtable in progress",
                "summary": f"Round {state.round_number} of 3.",
                "sections": [
                    {
                        "heading": "Seat progress",
                        "blocks": [{"kind": "timeline", "items": items}],
                    }
                ],
            }
        if state.stage == "checkpoint":
            actions = []
            if self._can_run_next_round(state):
                actions.append({"id": "next_round", "label": "Run another round"})
            actions.append({"id": "synthesize", "label": "Synthesize"})
            return {
                "id": "execution",
                "title": "Roundtable checkpoint",
                "summary": f"Round {state.round_number} is recorded.",
                "sections": [
                    {
                        "heading": "Receipts",
                        "blocks": [
                            {
                                "kind": "evidence",
                                "items": [
                                    {
                                        "label": receipt.seat,
                                        "value": (
                                            str(receipt.message_id)
                                            if receipt.message_id is not None
                                            else "unrecorded"
                                        ),
                                        "status": receipt.status,
                                    }
                                    for receipt in state.seat_receipts
                                ],
                            }
                        ],
                    }
                ],
                "actions": actions,
            }
        if state.stage == "triage":
            candidate = state.candidates[state.triage_index]
            actions = [
                {
                    "id": "promote",
                    "label": "Promote",
                    "consequence": "Authorize this board message for tracked promotion.",
                    "requires_explicit_choice": True,
                },
                {"id": "decline", "label": "Decline"},
            ]
            if self._can_run_next_round(state):
                actions.append({"id": "another_round", "label": "Another round"})
            return {
                "id": "execution",
                "title": "Roundtable promotion triage",
                "summary": (
                    f"Item {state.triage_index + 1} of {len(state.candidates)} "
                    "— one bounded decision per page."
                ),
                "sections": [
                    {
                        "heading": candidate.title,
                        "tone": "recommendation",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {
                                        "label": "Board message",
                                        "value": str(candidate.message_id),
                                    },
                                    {"label": "Proposal", "value": candidate.detail},
                                ],
                            }
                        ],
                    }
                ],
                "actions": actions,
            }
        promoted = ", ".join(str(item) for item in state.promoted_ids) or "none"
        return {
            "id": "receipt",
            "title": "Roundtable receipt",
            "summary": "Terminal record of the moderated deliberation.",
            "sections": [
                {
                    "heading": "Outcome",
                    "tone": "success",
                    "blocks": [
                        {
                            "kind": "key_value",
                            "items": [
                                {"label": "Thread", "value": state.thread_id},
                                {"label": "Rounds", "value": str(state.round_number)},
                                {"label": "Promoted message ids", "value": promoted},
                                {
                                    "label": "Halt reason",
                                    "value": state.halt_reason or "completed",
                                },
                            ],
                        },
                        {
                            "kind": "disclosure",
                            "title": "Synthesis",
                            "body": state.synthesis or "No synthesis was recorded.",
                        },
                    ],
                }
            ],
        }

    @staticmethod
    def _can_run_next_round(state: RoundtableWorkspaceState) -> bool:
        next_round = state.round_number + 1
        return next_round <= 3 and next_round * len(CANONICAL_SEATS) <= state.max_invocations
