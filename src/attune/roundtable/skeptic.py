"""Rotating skeptic for spec-closure claims — round-table P3.

Ruled 2026-07-21 (thread ``q-roundtable-extensions-001``, chair:
Patrick; build order P3 → P2 → P4-recording). V1 shape, R1-pure:
when a spec closure entry is staged, the HARNESS re-runs the
closure's declared cheap receipt commands (reusing
:func:`attune.roundtable.solutions.validate`, isolated in a
detached scratch worktree) and feeds the raw output as TEXT to a
rotation-picked NON-AUTHOR seat, which emits a structured
COUNTERSIGN or DISSENT citing the exact command + tail.

Governance (substrate-enforced, never seat-defined):

- **Different-model rule** — the skeptic is never the closure's
  author seat; :func:`skeptic_for` cannot return the author.
- **One skeptic pass** — a DISSENT gets ONE author bounce
  (solution-loop precedent; counts against the invocation cap),
  then everything goes to the chair digest. No auto-resolution.
- **Chair-only promotion** — this module never flips a spec
  status and never promotes a thread (R8).
- **TAC-4** — malformed verdicts and absent seats are recorded
  as such for the chair, never laundered into a countersign.

Failure modes on record (the ruling, verbatim concerns):
rubber-stamp decay; spurious environment dissents training the
chair to ignore dissent. The brief instructs the seat on both;
P4 role telemetry (record-only) will measure dissent hit-rate
once it launches.

Declared-receipt contract — a closure entry declares its cheap
receipts as structured lines (the ``P4-ROTATION:`` /
``PHASE-WAIVED:`` chair-line pattern)::

    RECEIPT-CMD: <label> :: <command and args>

Commands are shlex-split and run with fixed argv (never a
shell) inside the scratch worktree.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime
import re
import shlex
import subprocess  # nosec B404 — fixed argv git commands, never shell=True
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from attune.roundtable.rotation import CANONICAL_SEATS
from attune.roundtable.solutions import Candidate, CheckReceipt, discard, validate

#: Cheap receipts only — a closure declaring more than this is not
#: declaring *cheap* receipts and fails loudly for the chair.
MAX_RECEIPT_CMDS = 5

#: Invocation cap for one pass: skeptic attempt, one absent-fallback
#: attempt on the remaining eligible seat, one author bounce.
PASS_MAX_INVOCATIONS = 3

_RECEIPT_CMD_RE = re.compile(
    r"^\+?\s*RECEIPT-CMD:\s*(?P<label>[^:]+?)\s*::\s*(?P<cmd>.+?)\s*$",
    re.MULTILINE,
)

_VERDICT_RE = re.compile(r"^\s*VERDICT:\s*(?P<kind>COUNTERSIGN|DISSENT)\s*$", re.MULTILINE)
_CITE_RE = re.compile(r"^\s*CITE:\s*(?P<cite>.+?)\s*$", re.MULTILINE)
_REASON_RE = re.compile(r"^\s*REASON:\s*(?P<reason>.+?)\s*$", re.MULTILINE)

_GIT_TIMEOUT = 120


class SkepticError(ValueError):
    """A closure declaration this module refuses to act on."""


@dataclass(frozen=True)
class SkepticVerdict:
    """The parsed seat verdict — or the fact that it did not parse."""

    kind: str  # countersign | dissent | malformed
    cite: str | None = None
    reason: str | None = None
    raw: str = ""


@dataclass
class SkepticPass:
    """One complete pass — everything the chair digest needs."""

    spec: str
    author: str
    skeptic: str | None
    receipts: list[CheckReceipt] = field(default_factory=list)
    verdict: SkepticVerdict | None = None
    bounce_reply: str | None = None
    outcome: str = "pending"
    invocations: int = 0
    isolation_gap: list[str] = field(default_factory=list)


def parse_receipt_commands(text: str) -> list[tuple[str, list[str]]]:
    """Extract ``RECEIPT-CMD:`` declarations from a closure entry.

    Lines may carry a leading ``+`` (staged-diff form). Returns
    ``(label, argv)`` pairs in declaration order.

    Raises:
        SkepticError: More than :data:`MAX_RECEIPT_CMDS` declarations,
            a duplicate label, or a command that shlex cannot split.
    """
    checks: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for m in _RECEIPT_CMD_RE.finditer(text):
        label = m.group("label").strip()
        if label in seen:
            raise SkepticError(f"duplicate RECEIPT-CMD label: {label!r}")
        seen.add(label)
        try:
            argv = shlex.split(m.group("cmd"))
        except ValueError as exc:
            raise SkepticError(f"unparseable RECEIPT-CMD {label!r}: {exc}") from exc
        if not argv:
            raise SkepticError(f"empty RECEIPT-CMD: {label!r}")
        checks.append((label, argv))
    if len(checks) > MAX_RECEIPT_CMDS:
        raise SkepticError(
            f"{len(checks)} RECEIPT-CMD lines — cheap receipts are capped at {MAX_RECEIPT_CMDS}"
        )
    return checks


def staged_closure_text(repo: Path, spec_dir: str) -> str:
    """Return the ADDED lines of the spec's staged/working decisions diff.

    "Staged" per the ruling means the closure entry exists in the
    working tree but is not yet committed: ``git diff HEAD`` over the
    spec's ``decisions.md``, added lines only, ``+`` stripped.

    Raises:
        SkepticError: The git diff itself failed — an empty result
            must mean "no staged closure", never a masked git error.
    """
    proc = subprocess.run(  # nosec B603 — fixed argv, shell=False
        ["git", "-C", str(repo), "diff", "HEAD", "--", f"{spec_dir}/decisions.md"],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if proc.returncode != 0:
        raise SkepticError(f"git diff failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}")
    added = [
        line[1:]
        for line in proc.stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    return "\n".join(added)


def skeptic_for(author: str, records: Sequence[Mapping[str, object]]) -> str:
    """Pick the rotation-owed NON-AUTHOR skeptic seat (pure).

    Walks the canonical cycle starting after the last SERVED
    skeptic; the author seat is skipped (different-model rule).
    Unserved records never advance the pointer (the RR-2 semantic).

    Raises:
        SkepticError: Unknown author seat.
    """
    if author not in CANONICAL_SEATS:
        raise SkepticError(f"unknown author seat: {author!r}")
    start = 0
    for record in reversed(records):
        if bool(record.get("served")) and record.get("actual_skeptic") in CANONICAL_SEATS:
            last = str(record["actual_skeptic"])
            start = (CANONICAL_SEATS.index(last) + 1) % len(CANONICAL_SEATS)
            break
    for offset in range(len(CANONICAL_SEATS)):
        seat = CANONICAL_SEATS[(start + offset) % len(CANONICAL_SEATS)]
        if seat != author:
            return seat
    raise SkepticError("no eligible skeptic seat")  # pragma: no cover — 3 seats, 1 author


def rerun_receipts(
    repo: Path,
    checks: list[tuple[str, list[str]]],
    base_ref: str = "HEAD",
    scratch_root: Path | None = None,
) -> list[CheckReceipt]:
    """Re-run declared receipts ISOLATED — detached scratch worktree.

    Reuses :func:`attune.roundtable.solutions.validate` for the
    serial execution + tail receipts (the ruling's named mechanism);
    the worktree is always discarded, pass or fail.

    Isolation contract: the worktree is created from ``base_ref``
    (committed state) — uncommitted changes are NOT validated. Use
    :func:`uncommitted_paths` to surface that gap to the chair.

    Raises:
        RuntimeError: Scratch worktree creation failed.
    """
    root = scratch_root or Path(tempfile.gettempdir())
    worktree = root / f"rt-skeptic-{uuid.uuid4().hex[:12]}"
    created = subprocess.run(  # nosec B603 — fixed argv, shell=False
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), base_ref],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if created.returncode != 0:
        raise RuntimeError(f"worktree add failed: {created.stderr.strip()[:300]}")
    candidate = Candidate(worktree=worktree, files=[])
    try:
        return validate(candidate, checks).receipts
    finally:
        discard(candidate)


def uncommitted_paths(repo: Path, exclude: Sequence[str] = ()) -> list[str]:
    """Paths whose working state differs from HEAD (staged, unstaged,
    or untracked) — the receipts' isolation blind spot.

    The scratch worktree re-runs receipts from COMMITTED state, so
    any path listed here is invisible to what the skeptic validates.
    ``exclude`` names expected-uncommitted paths (the staged closure
    entry itself).

    Raises:
        SkepticError: ``git status`` failed.
    """
    proc = subprocess.run(  # nosec B603 — fixed argv, shell=False
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if proc.returncode != 0:
        raise SkepticError(
            f"git status failed (exit {proc.returncode}): {proc.stderr.strip()[:300]}"
        )
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:  # rename: validate the destination
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path and path not in exclude:
            paths.append(path)
    return paths


def _format_receipts(receipts: Sequence[CheckReceipt]) -> str:
    blocks = []
    for r in receipts:
        status = "PASS" if r.passed else f"FAIL (exit {r.exit_code})"
        blocks.append(f"### {r.label}: {status}\n$ {shlex.join(r.argv)}\n{r.tail}")
    return "\n\n".join(blocks)


def build_skeptic_brief(
    spec: str,
    closure_text: str,
    receipts: Sequence[CheckReceipt],
    isolation_gap: Sequence[str] = (),
) -> str:
    """Build the R1 text-only brief for the skeptic seat.

    ``isolation_gap`` names uncommitted paths the receipts could not
    see; the seat (and chair digest) must weigh the evidence knowing
    the blind spot exists — TAC-4 honesty over silent omission.
    """
    gap_note = ""
    if isolation_gap:
        shown = "\n".join(f"- {p}" for p in list(isolation_gap)[:20])
        more = len(isolation_gap) - 20
        if more > 0:
            shown += f"\n- … and {more} more"
        gap_note = (
            "\n\n## Isolation note\nReceipts were re-run from COMMITTED "
            "state; these uncommitted paths are NOT reflected in the "
            f"evidence:\n{shown}"
        )
    return (
        "You are the rotating SKEPTIC seat at a three-model round "
        f"table. A closure entry for spec {spec!r} is staged. The "
        "harness has RE-RUN the closure's declared receipt commands "
        "in an isolated worktree; the raw results are below. Judge "
        "ONLY from this evidence — do not run tools or invent checks "
        "that were not run.\n\n"
        "Reply with EXACTLY one verdict block:\n\n"
        "VERDICT: COUNTERSIGN\n"
        "CITE: <label> :: <the command you weight most>\n\n"
        "or\n\n"
        "VERDICT: DISSENT\n"
        "CITE: <label> :: <the failing command>\n"
        "REASON: <one line, grounded in that command's output tail>\n\n"
        "Calibration: a countersign you did not check for is "
        "rubber-stamp decay; an environment failure (exit 127 "
        "not-found, 124 timeout) earns a DISSENT only when it blocks "
        "the closure claim itself — spurious environment dissents "
        "train the chair to ignore dissent. Text only.\n\n"
        f"## Staged closure entry\n{closure_text}\n\n"
        f"## Re-run receipts\n{_format_receipts(receipts)}" + gap_note
    )


def build_bounce_brief(spec: str, verdict: SkepticVerdict, receipts: Sequence[CheckReceipt]) -> str:
    """Build the ONE author-bounce brief for a dissent (R1 text-only)."""
    return (
        f"You are the AUTHOR seat of the staged closure for spec "
        f"{spec!r}. The rotating skeptic DISSENTED:\n\n"
        f"CITE: {verdict.cite}\nREASON: {verdict.reason or '(none given)'}\n\n"
        "This is your ONE bounce before the chair digest. Either "
        "concede (say what the closure entry must change) or rebut, "
        "citing the exact receipt evidence below. Text only.\n\n"
        f"## Re-run receipts\n{_format_receipts(receipts)}"
    )


def parse_skeptic_verdict(text: str, valid_labels: Sequence[str] | None = None) -> SkepticVerdict:
    """Parse the seat reply into a verdict — malformed is a verdict.

    EVERY verdict must carry a CITE (an uncited COUNTERSIGN is the
    rubber stamp the ruling names as failure mode #1; a DISSENT
    without the exact command cannot be bounced). When
    ``valid_labels`` is given, the CITE's label part (before ``::``)
    must name an executed receipt — an invented citation is
    malformed, never recorded as valid. Nothing is laundered to
    countersign.
    """
    m = _VERDICT_RE.search(text)
    if not m:
        return SkepticVerdict(kind="malformed", raw=text)
    kind = m.group("kind").lower()
    cite_m = _CITE_RE.search(text)
    reason_m = _REASON_RE.search(text)
    cite = cite_m.group("cite") if cite_m else None
    reason = reason_m.group("reason") if reason_m else None
    if not cite:
        return SkepticVerdict(kind="malformed", cite=None, reason=reason, raw=text)
    if valid_labels is not None:
        label = cite.split("::", 1)[0].strip()
        if label not in valid_labels:
            return SkepticVerdict(kind="malformed", cite=cite, reason=reason, raw=text)
    return SkepticVerdict(kind=kind, cite=cite, reason=reason, raw=text)


def run_skeptic_pass(
    spec: str,
    closure_text: str,
    repo: Path,
    author: str,
    board: object | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    seat_recipes: Sequence[tuple[str, tuple[str, ...]]] | None = None,
    prior_records: Sequence[Mapping[str, object]] = (),
    thread: str | None = None,
    scratch_root: Path | None = None,
    spec_dir: str | None = None,
) -> SkepticPass:
    """Run ONE skeptic pass over a staged closure; return the record.

    Sequence: parse declared receipts → re-run isolated → rotation-
    pick a non-author seat → one verdict invocation (one absent
    fallback to the remaining eligible seat) → on DISSENT, one
    author bounce → post the pass to the board thread for the chair.
    Never flips a status, never promotes (R8).

    When ``spec_dir`` is given, uncommitted paths other than the
    spec's own ``decisions.md`` are recorded as the isolation gap
    (receipts validate committed state only) and surfaced in both
    the brief and the chair digest.
    """
    from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

    invoke = invoke_seat or default_invoke_seat
    recipes = dict(seat_recipes or SEAT_RECIPES)
    record = SkepticPass(spec=spec, author=author, skeptic=None)
    thread = thread or (f"skeptic-{spec}-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}")

    try:
        checks = parse_receipt_commands(closure_text)
    except SkepticError as exc:
        record.outcome = "bad-declaration"
        _post(board, thread, "moderator", "halt", f"skeptic pass refused: {exc}")
        return record
    if not checks:
        record.outcome = "no-receipts"
        _post(
            board,
            thread,
            "moderator",
            "halt",
            f"closure for {spec!r} declares no RECEIPT-CMD lines — "
            "nothing to countersign; chair reviews unassisted",
        )
        return record

    record.receipts = rerun_receipts(repo, checks, scratch_root=scratch_root)
    exclude = (f"{spec_dir}/decisions.md",) if spec_dir else ()
    record.isolation_gap = uncommitted_paths(repo, exclude=exclude) if spec_dir else []
    brief = build_skeptic_brief(spec, closure_text, record.receipts, record.isolation_gap)
    _post(board, thread, "moderator", "question", brief, skeptic_pass=spec)

    eligible = [seat for seat in _rotation_order(author, prior_records) if seat in recipes]
    for seat in eligible[:2]:  # picked seat + one absent fallback
        if record.invocations >= PASS_MAX_INVOCATIONS:
            break
        record.invocations += 1
        code, reply = invoke(recipes[seat], brief)
        if code != 0 or not reply.strip():
            _post(
                board,
                thread,
                seat,
                "position",
                f"ABSENT — exit {code}: {reply[:200]}",
                absent=True,
                skeptic_pass=spec,
            )
            continue
        record.skeptic = seat
        record.verdict = parse_skeptic_verdict(
            reply, valid_labels=[r.label for r in record.receipts]
        )
        _post(board, thread, seat, "position", reply, skeptic_pass=spec)
        break

    if record.skeptic is None:
        record.outcome = "skeptic-absent"
        _post(
            board,
            thread,
            "moderator",
            "halt",
            f"no eligible skeptic seat reachable for {spec!r}; chair reviews unassisted",
        )
        return record

    verdict = record.verdict
    assert verdict is not None  # nosec B101 — set with record.skeptic above
    if verdict.kind == "countersign":
        record.outcome = "countersigned"
    elif verdict.kind == "malformed":
        record.outcome = "malformed-verdict"
    else:
        record.outcome = "dissent"
        if record.invocations < PASS_MAX_INVOCATIONS and author in recipes:
            record.invocations += 1
            code, reply = invoke(
                recipes[author], build_bounce_brief(spec, verdict, record.receipts)
            )
            if code == 0 and reply.strip():
                record.bounce_reply = reply
                _post(board, thread, author, "position", reply, bounce=True, skeptic_pass=spec)
            else:
                _post(
                    board,
                    thread,
                    author,
                    "position",
                    f"ABSENT on bounce — exit {code}: {reply[:200]}",
                    absent=True,
                    skeptic_pass=spec,
                )

    _post(
        board,
        thread,
        "moderator",
        "synthesis",
        _digest(record),
        skeptic_pass=spec,
    )
    return record


def _rotation_order(author: str, records: Sequence[Mapping[str, object]]) -> list[str]:
    """Eligible seats in rotation order — owed seat first, author never."""
    first = skeptic_for(author, records)
    start = CANONICAL_SEATS.index(first)
    ordered = [
        CANONICAL_SEATS[(start + i) % len(CANONICAL_SEATS)] for i in range(len(CANONICAL_SEATS))
    ]
    return [seat for seat in ordered if seat != author]


def _digest(record: SkepticPass) -> str:
    """Compact chair-facing summary of one pass."""
    verdict = record.verdict
    lines = [
        f"Skeptic pass for {record.spec!r}: outcome={record.outcome}",
        f"author={record.author} skeptic={record.skeptic or 'ABSENT'}",
        "receipts: "
        + "; ".join(
            f"{r.label}={'PASS' if r.passed else f'FAIL({r.exit_code})'}" for r in record.receipts
        ),
    ]
    if verdict and verdict.kind == "dissent":
        lines.append(f"DISSENT cite: {verdict.cite}; reason: {verdict.reason or '(none)'}")
        lines.append("author bounce: " + ("recorded" if record.bounce_reply else "absent/none"))
    if record.isolation_gap:
        lines.append(
            f"isolation gap: {len(record.isolation_gap)} uncommitted path(s) "
            "NOT validated by the receipts"
        )
    lines.append("Chair rules; this pass never flips the spec status (R8).")
    return "\n".join(lines)


def _post(
    board: object | None, thread: str, seat: str, kind: str, body: str, **fields: object
) -> None:
    """Post to the board when one is wired; print otherwise."""
    if board is None:
        print(f"[{thread}] {seat}/{kind}: {body[:160]}", flush=True)
        return
    board.post_message(thread, seat, kind, body, **fields)  # type: ignore[attr-defined]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``python -m attune.roundtable.skeptic <spec-dir> --author <seat>``.

    Reads the staged (uncommitted) closure entry from the spec's
    ``decisions.md`` diff. ``--dry-run`` re-runs receipts and prints
    the brief without any board write or LLM invocation.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Rotating skeptic pass over a staged spec closure (P3; chair-only promotion)."
    )
    parser.add_argument("spec_dir", help="spec directory, e.g. docs/specs/<slug>")
    parser.add_argument("--author", required=True, choices=sorted(CANONICAL_SEATS))
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    spec = Path(args.spec_dir).name
    closure = staged_closure_text(repo, args.spec_dir)
    if not closure.strip():
        print(f"no staged decisions.md changes under {args.spec_dir!r}; nothing to review")
        return 1
    if args.dry_run:
        checks = parse_receipt_commands(closure)
        if not checks:
            print("no RECEIPT-CMD declarations in the staged closure")
            return 1
        receipts = rerun_receipts(repo, checks)
        gap = uncommitted_paths(repo, exclude=(f"{args.spec_dir}/decisions.md",))
        print(build_skeptic_brief(spec, closure, receipts, gap))
        return 0

    from attune.roundtable.board import Board

    record = run_skeptic_pass(
        spec, closure, repo, args.author, board=Board(), spec_dir=args.spec_dir
    )
    print(f"skeptic pass complete: outcome={record.outcome}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
