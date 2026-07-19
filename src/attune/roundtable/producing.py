"""Producing routine — headless spec-authoring runs (round-table V2-P4).

Implements RR-3 (absence semantics), RR-5 (the role-aware loop state
machine with compiler-lint gates and the chair-ratified
``max_invocations = 10``), RR-6 (R8-absolute staging under the TR-6
cap of 7), and RR-7 (the closed failure taxonomy with typed
receipts) from ``docs/specs/roundtable-producing-team/
p4-requirements.md`` (thread ``table-p4-001``).

Shape: one producing run = one board thread = one spec subject.
Three structural rounds (draft → critique → final), each output
gated by the V2-P2 compiler lints BEFORE posting; lint repairs are
intra-round (they count against R5 only, never D3). A headless run
assembles an UNRULED candidate compilation — ``compile_requirements``
with empty rulings — never final assembly; the chair rules per item
afterwards (R8: the routine never promotes).

Two taxonomy codes are RESERVED here — raised by moderator-side
orchestration, not by this state machine: ``ROUND_CEILING`` (the
three structural rounds are fixed by construction) and
``MATERIALIZE_FAILED`` (scratch materialization for chair diffing is
a post-run moderator step via ``solutions.materialize``).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from attune.roundtable import compiler
from attune.roundtable.board import Board
from attune.roundtable.rotation import (
    CANONICAL_SEATS,
    FIXED_DRAFTER,
    assignments_for,
    next_owed,
)
from attune.roundtable.routine import (
    CHECK_TIMEOUT,
    SEAT_RECIPES,
    default_invoke_seat,
    run_command,
)

#: The closed RR-7 failure/degradation taxonomy. Adding a code
#: requires a spec amendment — unclassifiable conditions are
#: implementation bugs, not quiet new categories.
FAILURE_CODES: tuple[str, ...] = (
    "INPUT_INVALID",
    "PRECHECK_FAILED",
    "DUPLICATE_RUN",
    "SEAT_ABSENT",
    "UNCRITIQUED",
    "LINT_DIRTY",
    "ROUND_CEILING",
    "BUDGET_EXHAUSTED",
    "COMPILE_ERROR",
    "MATERIALIZE_FAILED",
    "BOARD_WRITE_FAILED",
    "BOARD_UNREACHABLE",
)

#: Verbatim-evidence cap (RR-7) — bounds stored provider output.
EVIDENCE_CHARS = 2_000

#: TR-6: staged promotable candidates per session (chair-ruled 7,
#: 2026-07-19). Overflow is held on the thread as deferred_over_cap —
#: full text preserved, restageable in a chair-initiated session.
TR6_CAP = 7

#: R5 cap for producing mode (chair-RATIFIED 10, 2026-07-19): 4 role
#: invocations + 4 repairs + 2 absence-discovery margin. Failed
#: attempts and repairs count; deterministic lints and compile don't.
DEFAULT_MAX_INVOCATIONS = 10

_RECIPES: dict[str, tuple[str, ...]] = dict(SEAT_RECIPES)


@dataclass
class FailureReceipt:
    """One typed RR-7 receipt. ``evidence`` only where output exists."""

    code: str
    run_id: str
    thread: str | None = None
    round: int | None = None
    seat: str | None = None
    role: str | None = None
    detail: str = ""
    evidence: str | None = None

    def __post_init__(self) -> None:
        if self.code not in FAILURE_CODES:
            raise ValueError(f"unknown failure code: {self.code!r}")
        if self.evidence is not None:
            self.evidence = self.evidence[-EVIDENCE_CHARS:]

    def to_dict(self) -> dict[str, Any]:
        """Structured form for digests and out-of-band receipts."""
        out: dict[str, Any] = {"code": self.code, "run_id": self.run_id}
        for key in ("thread", "round", "seat", "role"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.detail:
            out["detail"] = self.detail
        if self.evidence is not None:
            out["evidence"] = self.evidence
        return out


@dataclass
class ProducingSpec:
    """One producing run's input contract (RR-5).

    Args:
        slug: Spec slug; the run/thread id is
            ``producing-<slug>-<slot>``.
        subject: Human spec subject (the compiled document's title).
        grounding_pack: Path to the moderator-prepared grounding pack.
        slot: Stable run-identity component (e.g. a schedule slot or
            date stamp) — supplied by the caller, per-spec arming.
        checks: ``(label, argv)`` keyless prechecks (may be empty).
        max_invocations: R5 cap (chair-ratified default 10).
    """

    slug: str
    subject: str
    grounding_pack: str | Path
    slot: str
    checks: Sequence[tuple[str, Sequence[str]]] = ()
    max_invocations: int = DEFAULT_MAX_INVOCATIONS

    @property
    def run_id(self) -> str:
        """Stable run identity: ``producing-<slug>-<slot>``."""
        return f"producing-{self.slug}-{self.slot}"


@dataclass
class ProducingResult:
    """What a producing run yielded — status is never laundered."""

    run_id: str
    thread: str | None
    status: str  # clean | degraded | failed
    receipts: list[FailureReceipt] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    invocations: int = 0


def _default_invoke(seat: str, role: str, brief: str) -> tuple[int, str]:
    """Invoke a seat CLI with its role-aware reply budget (RR-5)."""
    budget = compiler.ROLE_REPLY_CHARS.get(role, compiler.ROLE_REPLY_CHARS["position"])
    return default_invoke_seat(_RECIPES[seat], brief, reply_chars=budget)


def _draft_brief(subject: str, pack: str) -> str:
    return (
        "You are the DRAFTER seat in a headless spec-authoring round "
        "table. Work ONLY from the grounding pack. Text only — no "
        "tools, no files. Produce the round-1 draft for: "
        f"{subject}\n\nFORMAT (mechanically linted): a '## Requirements' "
        f"section with AT MOST {TR6_CAP} items, each heading exactly "
        "'**RR-N — title**' followed by a rationale and '- ' acceptance "
        "bullets (>=2); a '## Non-goals' section; optionally "
        "'## Open questions'.\n\nGROUNDING PACK:\n\n" + pack
    )


def _critique_brief(subject: str, pack: str, draft: str) -> str:
    return (
        "You are a CRITIC seat in a headless spec-authoring round "
        "table. Adversarially critique the draft below. Text only.\n\n"
        "FORMAT (mechanically linted): a numbered list; each item names "
        "a target id in bold (e.g. **RR-2:**) or **MISSING:**, and "
        "cites a pack item or concrete file path; end with exactly one "
        "line 'VERDICT: ready-with-edits' or 'VERDICT: needs-revision'."
        f"\n\nSUBJECT: {subject}\n\nGROUNDING PACK:\n\n{pack}"
        f"\n\nTHE DRAFT:\n\n{draft}"
    )


#: Literal worked example of a tagged item. Prose alone was not
#: enough: two live headless runs had the drafter fail lint_final
#: with every item untagged, twice each, until the brief showed
#: this exact shape (receipts in the roundtable-producing-team
#: spec's decisions.md).
TAG_EXAMPLE = (
    "EXAMPLE ITEM (copy this shape — the tag line sits alone on the "
    "line immediately after the heading):\n"
    "**RR-1 — Example requirement title**\n"
    "[tag: agreed]\n"
    "One-sentence rationale for the requirement.\n"
    "- first acceptance bullet\n"
    "- second acceptance bullet"
)


def _final_brief(subject: str, draft: str, critiques: dict[str, str]) -> str:
    parts = [
        "You are the DRAFTER seat. Revise your draft into the round-3 "
        "FINAL. Text only.\n\nFORMAT (mechanically linted): same item "
        "format; immediately after each heading a convergence tag line "
        "'[tag: agreed]' / '[tag: 2-1 <note>]' / '[tag: contested "
        "<note>]'; a '## Non-goals' section; a '## Dissent register' "
        "section (or the literal attestation 'Empty — attested').",
        TAG_EXAMPLE,
        f"SUBJECT: {subject}",
        f"YOUR DRAFT:\n\n{draft}",
    ]
    for seat in sorted(critiques):
        parts.append(f"CRITIQUE ({seat}):\n\n{critiques[seat]}")
    if not critiques:
        parts.append("CRITIQUES: MISSING — no critic was available this run.")
    return "\n\n".join(parts)


def _repair_brief(brief: str, reply: str, problems: list[str]) -> str:
    parts = [
        "Your previous reply failed the mechanical lint. Problems:\n- " + "\n- ".join(problems)
    ]
    if any("convergence tag" in p for p in problems):
        parts.append(
            "Every item heading must be followed by its own convergence "
            "tag line: '[tag: agreed]' / '[tag: 2-1 <note>]' / "
            "'[tag: contested <note>]'.\n\n" + TAG_EXAMPLE
        )
    parts.append("Fix ONLY these problems and resend the full document.")
    parts.append("ORIGINAL BRIEF:\n\n" + brief)
    parts.append("YOUR PREVIOUS REPLY:\n\n" + reply)
    return "\n\n".join(parts)


class _Terminal(Exception):
    """Internal: a typed terminal outcome carrying its receipt."""

    def __init__(self, receipt: FailureReceipt) -> None:
        super().__init__(receipt.code)
        self.receipt = receipt


def render_digest(
    status: str,
    receipts: Sequence[FailureReceipt],
    final: compiler.SpecDraft | None,
    staged: Sequence[str],
    deferred: Sequence[str],
) -> str:
    """Render the chair digest — failures and dissent BEFORE candidates.

    The ordering is the inverse of the tidy-queue shape (RR-7): the
    header enumerates every condition that occurred, then failures
    with receipts, then the dissent register and non-agreed items,
    then agreed candidates last.
    """
    codes = [r.code for r in receipts]
    lines = [
        f"status: {status}",
        "conditions: " + (", ".join(dict.fromkeys(codes)) if codes else "none"),
        f"staged: {len(staged)} | deferred_over_cap: {len(deferred)}",
    ]
    if receipts:
        lines.append("\n## Failures / degradations (receipts)")
        lines.extend(json.dumps(r.to_dict(), ensure_ascii=False) for r in receipts)
    if final is not None:
        contested = [i for i in final.items if i.tag and not i.tag.lower().startswith("agreed")]
        if final.dissent_register:
            lines.append("\n## Dissent register\n" + final.dissent_register)
        if contested:
            lines.append("\n## Non-agreed items")
            lines.extend(f"- {i.item_id} [{i.tag}] {i.title}" for i in contested)
        agreed = [i.item_id for i in final.items if i.tag.lower().startswith("agreed")]
        if agreed:
            lines.append("\n## Agreed candidates\n" + ", ".join(agreed))
    return "\n".join(lines)


class _ProducingRun:
    """One run's state: invocation accounting, receipts, conditions."""

    def __init__(
        self,
        spec: ProducingSpec,
        board: Board,
        invoke: Callable[[str, str, str], tuple[int, str]],
        armed: bool,
    ) -> None:
        self.spec = spec
        self.board = board
        self.invoke = invoke
        self.armed = armed
        self.thread = spec.run_id
        self.receipts: list[FailureReceipt] = []
        self.invocations = 0
        self.served_recorded = False

    def _receipt(self, code: str, **kw: Any) -> FailureReceipt:
        receipt = FailureReceipt(code=code, run_id=self.spec.run_id, thread=self.thread, **kw)
        self.receipts.append(receipt)
        return receipt

    def _spend(self, round_no: int) -> None:
        """Count one invocation; halt at the R5 cap (halt is posted)."""
        if self.invocations >= self.spec.max_invocations:
            self.board.post_message(
                self.thread,
                "moderator",
                "halt",
                f"invocation cap ({self.spec.max_invocations}) reached in round {round_no}",
            )
            raise _Terminal(
                self._receipt(
                    "BUDGET_EXHAUSTED",
                    round=round_no,
                    detail=f"cap {self.spec.max_invocations} reached",
                )
            )
        self.invocations += 1

    def _invoke_once(self, seat: str, role: str, brief: str, round_no: int) -> tuple[bool, str]:
        self._spend(round_no)
        code, reply = self.invoke(seat, role, brief)
        return (code == 0 and bool(reply.strip())), reply

    def _lint_gated(
        self,
        seat: str,
        role: str,
        brief: str,
        lint: Callable[[str], list[str]],
        round_no: int,
        retries: int,
    ) -> str:
        """Invoke with absence retries, then lint with ONE repair.

        Returns the lint-clean reply. Raises ``_Terminal`` on absence
        past retries (``SEAT_ABSENT``) or dirty-after-repair
        (``LINT_DIRTY``) — un-linted text never reaches the compiler.
        """
        ok, reply = self._invoke_once(seat, role, brief, round_no)
        attempts = 0
        while not ok and attempts < retries:
            attempts += 1
            ok, reply = self._invoke_once(seat, role, brief, round_no)
        if not ok:
            raise _Terminal(
                self._receipt(
                    "SEAT_ABSENT",
                    round=round_no,
                    seat=seat,
                    role=role,
                    detail="invocation failed after retry",
                    evidence=reply or None,
                )
            )
        problems = lint(reply)
        if problems:
            ok, repaired = self._invoke_once(
                seat, role, _repair_brief(brief, reply, problems), round_no
            )
            problems2 = lint(repaired) if ok else problems
            if not ok or problems2:
                raise _Terminal(
                    self._receipt(
                        "LINT_DIRTY",
                        round=round_no,
                        seat=seat,
                        role=role,
                        detail="dirty after the one repair round",
                        evidence="\n".join(problems2),
                    )
                )
            reply = repaired
        return reply

    def _post_failure_digest(self, status: str = "failed") -> None:
        digest = render_digest(status, self.receipts, None, [], [])
        self.board.post_message(self.thread, "moderator", "synthesis", digest, status=status)

    def run(self) -> ProducingResult:
        """Execute the state machine; every exit is typed (RR-5)."""
        import redis  # noqa: PLC0415 — optional dependency, import at use

        spec = self.spec

        # Assignment BEFORE reservation: the pointer reads the ledger
        # as it stood, not including this run's own record.
        records = self.board.ledger_read()
        owed = next_owed(records) if self.armed else FIXED_DRAFTER
        basis = "rotation" if self.armed else "fixed"

        # CAS reservation (RR-2): a duplicate run makes NO writes.
        try:
            self.board.ledger_reserve(spec.run_id, spec.subject, owed)
        except redis.ResponseError as exc:
            if "duplicate run_id" not in str(exc):
                raise
            receipt = FailureReceipt(code="DUPLICATE_RUN", run_id=spec.run_id, detail=str(exc))
            return ProducingResult(
                run_id=spec.run_id, thread=None, status="failed", receipts=[receipt]
            )

        # Input contract (RR-5): garbage input spends no invocations.
        try:
            pack = Path(spec.grounding_pack).read_text(encoding="utf-8")
        except OSError as exc:
            self._receipt("INPUT_INVALID", detail=f"grounding pack unreadable: {exc}")
            self._post_failure_digest()
            return self._result("failed", None)
        if not pack.strip():
            self._receipt("INPUT_INVALID", detail="grounding pack is empty")
            self._post_failure_digest()
            return self._result("failed", None)

        # Keyless prechecks (evidence discipline carried from clean-run).
        for label, argv in spec.checks:
            code, tail = run_command(argv, timeout=CHECK_TIMEOUT)
            if code != 0:
                self._receipt("PRECHECK_FAILED", detail=f"{label} exit {code}", evidence=tail)
                self._post_failure_digest()
                return self._result("failed", None)

        # Thread open: question + the RR-1 scheduled-assignment event
        # (no seat is briefed before the event exists).
        self.board.post_message(self.thread, "moderator", "question", pack, routine="producing")
        self.board.post_event(
            self.thread,
            "scheduled-assignment",
            run_id=spec.run_id,
            spec_subject=spec.subject,
            assignments=assignments_for(owed),
            basis=basis,
        )

        try:
            final_draft, staged, deferred = self._rounds(owed, pack)
        except _Terminal:
            # A drafter who delivered a lint-clean round-1 draft has
            # SERVED (RR-2) even when a later round fails — only mark
            # unserved when round 1 itself never completed.
            if not self.served_recorded:
                self.board.ledger_record(spec.run_id, "", served=False)
            self._post_failure_digest()
            return self._result("failed", None)
        status = "degraded" if self.receipts or deferred else "clean"
        digest = render_digest(status, self.receipts, final_draft, staged, deferred)
        self.board.post_message(self.thread, "moderator", "synthesis", digest, status=status)
        return self._result(status, staged, deferred)

    def _rounds(self, owed: str, pack: str) -> tuple[compiler.SpecDraft, list[str], list[str]]:
        spec = self.spec

        # Round 1 — drafter; absence at open substitutes down the
        # canonical order (RR-3), each failed attempt counted.
        drafter, draft = self._round_one(owed, pack)
        served_by_owed = drafter == owed
        self.board.ledger_record(spec.run_id, drafter, served=True)
        self.served_recorded = True
        self.board.post_message(self.thread, drafter, "position", draft, round=1, role="drafter")
        if not served_by_owed:
            self.board.post_event(
                self.thread, "fallback", fallback_from=owed, actual_drafter=drafter
            )

        # Round 2 — critics; an absent critic degrades, never blocks.
        critiques: dict[str, str] = {}
        for critic in [s for s in CANONICAL_SEATS if s != drafter]:
            try:
                critiques[critic] = self._lint_gated(
                    critic,
                    "critic",
                    _critique_brief(spec.subject, pack, draft),
                    compiler.lint_critique,
                    round_no=2,
                    retries=1,
                )
            except _Terminal as term:
                if term.receipt.code != "SEAT_ABSENT":
                    raise  # LINT_DIRTY terminates the run (RR-5)
                # recorded MISSING; the run continues (R6).
        for critic, text in critiques.items():
            self.board.post_message(
                self.thread,
                critic,
                "position",
                text,
                round=2,
                role="critic",
                verdict=compiler.critique_verdict(text),
            )
        if not critiques:
            # Chair ruling 2026-07-19: proceed + UNCRITIQUED flag
            # (R6 preserved; the abort alternative was declined).
            self._receipt("UNCRITIQUED", round=2, detail="zero critics available")

        # Round 3 — the drafter produces the tagged final itself; the
        # moderator lints and assembles but never authors (R1).
        final_text = self._lint_gated(
            drafter,
            "drafter",
            _final_brief(spec.subject, draft, critiques),
            compiler.lint_final,
            round_no=3,
            retries=1,
        )
        self.board.post_message(
            self.thread, drafter, "position", final_text, round=3, role="drafter"
        )

        # Unruled candidate compilation (RR-5) — never final assembly.
        try:
            final_draft = compiler.parse_draft(final_text)
            compiler.link_critiques(final_draft, critiques)
            compiler.compile_requirements(
                final_draft, spec_title=spec.subject, thread=self.thread, rulings={}
            )
        except _Terminal:
            raise
        except Exception as exc:
            raise _Terminal(
                self._receipt("COMPILE_ERROR", detail=f"{type(exc).__name__}: {exc}")
            ) from exc

        return final_draft, *self._stage(final_draft)

    def _round_one(self, owed: str, pack: str) -> tuple[str, str]:
        brief = _draft_brief(self.spec.subject, pack)
        order = (
            CANONICAL_SEATS[CANONICAL_SEATS.index(owed) :]
            + CANONICAL_SEATS[: CANONICAL_SEATS.index(owed)]
        )
        for seat in order:
            try:
                draft = self._lint_gated(
                    seat, "drafter", brief, compiler.lint_draft, round_no=1, retries=0
                )
                return seat, draft
            except _Terminal as term:
                if term.receipt.code != "SEAT_ABSENT":
                    raise  # LINT_DIRTY / BUDGET_EXHAUSTED terminate
        raise _Terminal(
            self._receipt("SEAT_ABSENT", round=1, role="drafter", detail="no seat available")
        )

    def _stage(self, final_draft: compiler.SpecDraft) -> tuple[list[str], list[str]]:
        uncritiqued = any(r.code == "UNCRITIQUED" for r in self.receipts)
        staged: list[str] = []
        deferred: list[str] = []
        for index, item in enumerate(final_draft.items):
            over_cap = index >= TR6_CAP
            extra: dict[str, Any] = {"item_id": item.item_id, "tag": item.tag}
            if uncritiqued:
                extra["uncritiqued"] = True
            if over_cap:
                extra["deferred_over_cap"] = True
            self.board.post_message(
                self.thread,
                "moderator",
                "candidate",
                f"**{item.item_id} — {item.title}**\n{item.body}",
                **extra,
            )
            (deferred if over_cap else staged).append(item.item_id)
        return staged, deferred

    def _result(
        self,
        status: str,
        staged: list[str] | None,
        deferred: list[str] | None = None,
    ) -> ProducingResult:
        return ProducingResult(
            run_id=self.spec.run_id,
            thread=self.thread,
            status=status,
            receipts=self.receipts,
            staged=staged or [],
            deferred=deferred or [],
            invocations=self.invocations,
        )


def run_producing(
    spec: ProducingSpec,
    board: Board | None = None,
    invoke: Callable[[str, str, str], tuple[int, str]] = _default_invoke,
    armed: bool = False,
    out: Callable[[str], None] = print,
) -> ProducingResult:
    """Run one headless producing loop end-to-end (RR-5).

    Every exit is typed: a lint-clean unruled candidate compilation
    staged on the board, or an RR-7 terminal with receipts. The
    routine NEVER promotes (R8) — candidates wait for the chair.

    Args:
        spec: The run's input contract.
        board: Board client; a default one when None.
        invoke: Seat invoker ``(seat, role, brief) -> (exit, reply)``
            (injectable for tests; the default applies role budgets).
        armed: True only after the chair's ``P4-ROTATION: armed``
            ruling (see ``rotation.rotation_status``); False = fixed
            roles per PACK-1.
        out: Sink for out-of-band receipts — the one failure class
            that cannot reach the board (``BOARD_UNREACHABLE``) and
            mid-run board-write failures land here (the launchd log
            surface), never silently.
    """
    import redis  # noqa: PLC0415 — optional dependency, import at use

    board = board or Board()
    try:
        board.ensure_functions()
    except redis.RedisError as exc:
        receipt = FailureReceipt(code="BOARD_UNREACHABLE", run_id=spec.run_id, detail=str(exc))
        out(json.dumps(receipt.to_dict(), ensure_ascii=False))
        return ProducingResult(run_id=spec.run_id, thread=None, status="failed", receipts=[receipt])
    try:
        return _ProducingRun(spec, board, invoke, armed).run()
    except redis.RedisError as exc:
        receipt = FailureReceipt(code="BOARD_WRITE_FAILED", run_id=spec.run_id, detail=str(exc))
        out(json.dumps(receipt.to_dict(), ensure_ascii=False))
        return ProducingResult(
            run_id=spec.run_id, thread=spec.run_id, status="failed", receipts=[receipt]
        )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m attune.roundtable.producing <slug> <subject> <pack> --slot <slot>``.

    Per-spec arming (chair-ruled): the chair queues a grounding pack
    per subject; there is no standing spec cadence. Rotation basis is
    computed from the owning spec's decisions.md (RR-4) — never
    self-armed.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run one headless producing loop (R8: never promotes)."
    )
    parser.add_argument("slug")
    parser.add_argument("subject")
    parser.add_argument("grounding_pack")
    parser.add_argument("--slot", required=True, help="stable run-identity component")
    parser.add_argument(
        "--decisions",
        default="docs/specs/roundtable-producing-team/decisions.md",
        help="decisions.md carrying P4-BASELINE / P4-ROTATION lines",
    )
    args = parser.parse_args(argv)

    from attune.roundtable.rotation import rotation_status

    try:
        status = rotation_status(Path(args.decisions).read_text(encoding="utf-8"))
        armed = status.state == "armed"
    except OSError:
        armed = False
    spec = ProducingSpec(
        slug=args.slug,
        subject=args.subject,
        grounding_pack=args.grounding_pack,
        slot=args.slot,
    )
    result = run_producing(spec, armed=armed)
    print(
        f"producing run {result.run_id}: {result.status} "
        f"({result.invocations} invocations, {len(result.staged)} staged, "
        f"{len(result.deferred)} deferred); the thread is NOT promoted (R8)."
    )
    return 0 if result.status != "failed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
