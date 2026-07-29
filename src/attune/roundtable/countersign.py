"""Hardened skeptic countersign of lead receipt re-runs — D11c.

Ruled 2026-07-29 (feature-lead-governance decisions.md D11c, via
roundtable ``q-lead-verification-gap-001``): the lead re-runs every
seat's receipts centrally, but nobody mechanically verifies the
lead's own re-runs. This module closes that gap in the HARDENED
form the table converged on — the naive form (skeptic judging
receipts the lead narrates in its own session) was rejected as
"self-verification with another prompt attached" (codex).

Evidence path: **executor → artifact → skeptic**.

1. :func:`rerun_receipts_to_artifact` executes the declared
   receipt commands in an isolated scratch worktree (same
   execution semantics as :func:`attune.roundtable.solutions.
   validate` — serial, fixed argv, never a shell) and appends one
   hash-chained JSONL entry per receipt AS IT COMPLETES. The
   writer refuses existing paths: append-only, no overwrite.
2. :func:`load_receipt_artifact` re-verifies the full digest
   chain and FAILS CLOSED — missing file, unparseable line,
   broken chain, or zero receipts is a :class:`CountersignError`,
   never a partial read.
3. :func:`run_countersign_pass` builds the seat brief
   mechanically from the verified artifact, rotation-picks a
   NON-LEAD seat (different-model rule, reusing
   :func:`attune.roundtable.skeptic.skeptic_for`), and parses the
   verdict with ``valid_labels`` drawn from the artifact — an
   invented CITE is malformed, never valid.
4. A verified COUNTERSIGN renders as a fixed-grammar ledger token
   (:func:`format_countersign_token`) carrying the seat, cited
   label, and artifact digest; the R5 ledger gate imports
   :data:`COUNTERSIGN_TOKEN_RE` so grammar and gate cannot drift.

The module can emit a token from exactly one path: verified
artifact + parsed COUNTERSIGN citing an executed receipt. Every
other outcome is a recorded refusal (TAC-4 — never laundered).
R8 intact: never flips a status, never promotes.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import shlex
import subprocess  # nosec B404 — fixed argv git commands, never shell=True
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from attune.roundtable.rotation import CANONICAL_SEATS
from attune.roundtable.skeptic import (
    MAX_RECEIPT_CMDS,
    SkepticVerdict,
    parse_skeptic_verdict,
    skeptic_for,
)
from attune.roundtable.solutions import Candidate, CheckReceipt, discard, validate

#: The ledger-citable token grammar — imported by
#: tests/unit/gates/test_ledger_countersign_format.py (one source).
COUNTERSIGN_TOKEN_RE = re.compile(
    r"(?P<kind>countersign|dissent): (?P<seat>[a-z][a-z0-9-]*) :: "
    r"(?P<label>[^:]+?) :: sha256:(?P<digest>[0-9a-f]{16,64})"
)

_ARTIFACT_VERSION = 1

_GIT_TIMEOUT = 120


class CountersignError(ValueError):
    """An artifact or invocation this module refuses to countersign."""


@dataclass(frozen=True)
class ReceiptArtifact:
    """A digest-verified receipt artifact — the skeptic's only input."""

    path: Path
    commit: str
    receipts: list[CheckReceipt]
    sha256: str  # digest of the artifact file bytes — the citable id


@dataclass
class CountersignPass:
    """One complete countersign pass — everything the chair needs."""

    lead: str
    artifact_sha256: str | None = None
    skeptic: str | None = None
    verdict: SkepticVerdict | None = None
    outcome: str = "pending"
    token: str | None = None
    receipts: list[CheckReceipt] = field(default_factory=list)


def _entry_digest(entry: Mapping[str, object]) -> str:
    """Canonical digest of one artifact entry (minus its own digest)."""
    material = {k: v for k, v in entry.items() if k != "entry_digest"}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _append_entry(handle, entry: dict, prev_digest: str) -> str:
    """Chain, digest, write, and flush one entry; return its digest."""
    entry["prev_digest"] = prev_digest
    entry["entry_digest"] = _entry_digest(entry)
    handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    handle.flush()
    return str(entry["entry_digest"])


def rerun_receipts_to_artifact(
    repo: Path,
    checks: list[tuple[str, list[str]]],
    artifact_path: Path,
    base_ref: str = "HEAD",
    scratch_root: Path | None = None,
) -> ReceiptArtifact:
    """Execute receipt commands isolated, streaming the artifact.

    This IS the executor: each :class:`CheckReceipt` is appended to
    the artifact the moment its command completes, by the same
    process that ran it — the lead never gets a window to narrate.
    Execution reuses :func:`attune.roundtable.solutions.validate`
    one check at a time (serial, fixed argv, tail truncation,
    127/124 mapping) inside a detached scratch worktree that is
    always discarded.

    Raises:
        CountersignError: ``artifact_path`` already exists (the
            artifact is append-only — never overwrite), no checks
            declared, or more than the cheap-receipt cap.
        RuntimeError: Scratch worktree creation failed.
    """
    if artifact_path.exists() or artifact_path.is_symlink():
        raise CountersignError(f"artifact path already exists (append-only): {artifact_path}")
    if not checks:
        raise CountersignError("no receipt commands to execute")
    if len(checks) > MAX_RECEIPT_CMDS:
        raise CountersignError(
            f"{len(checks)} receipt commands — cheap receipts are capped at {MAX_RECEIPT_CMDS}"
        )
    for label, _ in checks:
        # Labels flow into the ledger token grammar; a colon would
        # make the eventual countersign unrenderable — refuse at the
        # executor end, not after the seat has already voted.
        if not label or ":" in label:
            raise CountersignError(f"receipt label unusable in token grammar: {label!r}")
    resolved = subprocess.run(  # nosec B603 — fixed argv, shell=False
        ["git", "-C", str(repo), "rev-parse", base_ref],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if resolved.returncode != 0:
        raise CountersignError(f"cannot resolve {base_ref!r}: {resolved.stderr.strip()[:300]}")
    commit = resolved.stdout.strip()

    root = scratch_root or Path(tempfile.gettempdir())
    worktree = root / f"rt-countersign-{uuid.uuid4().hex[:12]}"
    created = subprocess.run(  # nosec B603 — fixed argv, shell=False
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), base_ref],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT,
    )
    if created.returncode != 0:
        raise RuntimeError(f"worktree add failed: {created.stderr.strip()[:300]}")

    candidate = Candidate(worktree=worktree, files=[])
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with artifact_path.open("x", encoding="utf-8") as handle:
            prev = _append_entry(
                handle,
                {
                    "seq": 0,
                    "kind": "header",
                    "version": _ARTIFACT_VERSION,
                    "commit": commit,
                    "declared": [[label, list(argv)] for label, argv in checks],
                    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
                prev_digest="",
            )
            for seq, (label, argv) in enumerate(checks, start=1):
                validate(candidate, [(label, argv)])
                receipt = candidate.receipts[-1]
                prev = _append_entry(
                    handle,
                    {
                        "seq": seq,
                        "kind": "receipt",
                        "label": receipt.label,
                        "argv": receipt.argv,
                        "exit_code": receipt.exit_code,
                        "tail": receipt.tail,
                        "tail_sha256": hashlib.sha256(receipt.tail.encode("utf-8")).hexdigest(),
                    },
                    prev_digest=prev,
                )
    finally:
        discard(candidate)
    return ReceiptArtifact(
        path=artifact_path,
        commit=commit,
        receipts=list(candidate.receipts),
        sha256=hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
    )


def _parse_artifact_lines(artifact_path: Path) -> tuple[bytes, list[dict]]:
    """Read the artifact and parse one JSON object per line — FAIL CLOSED."""
    if artifact_path.is_symlink():
        raise CountersignError(f"artifact is a symlink (refused): {artifact_path}")
    if not artifact_path.is_file():
        raise CountersignError(f"artifact missing: {artifact_path}")
    raw = artifact_path.read_bytes()
    lines = raw.decode("utf-8", errors="strict").splitlines() if raw else []
    if not lines:
        raise CountersignError(f"artifact empty: {artifact_path}")
    entries: list[dict] = []
    for n, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CountersignError(f"artifact line {n} unparseable: {exc}") from exc
        if not isinstance(entry, dict):
            raise CountersignError(f"artifact line {n} is not an object")
        entries.append(entry)
    return raw, entries


def _validate_header(entries: list[dict]) -> dict:
    """The artifact must open with a supported-version header entry."""
    header = entries[0]
    if header.get("kind") != "header" or header.get("seq") != 0:
        raise CountersignError("artifact does not start with a header entry")
    if header.get("version") != _ARTIFACT_VERSION:
        raise CountersignError(f"unsupported artifact version: {header.get('version')!r}")
    return header


def _receipt_from_entry(entry: dict, n: int) -> CheckReceipt:
    """Validate one receipt entry and build its CheckReceipt — FAIL CLOSED."""
    if entry.get("kind") != "receipt" or entry.get("seq") != n:
        raise CountersignError(f"bad sequence at entry {n}")
    tail = entry.get("tail")
    if not isinstance(tail, str) or not isinstance(entry.get("label"), str):
        raise CountersignError(f"malformed receipt entry {n}")
    if hashlib.sha256(tail.encode("utf-8")).hexdigest() != entry.get("tail_sha256"):
        raise CountersignError(f"tail digest mismatch at entry {n}")
    argv = entry.get("argv")
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        raise CountersignError(f"malformed argv at entry {n}")
    return CheckReceipt(
        label=entry["label"],
        argv=list(argv),
        exit_code=int(entry.get("exit_code", -1)),
        tail=tail,
    )


def load_receipt_artifact(artifact_path: Path) -> ReceiptArtifact:
    """Load and digest-verify an artifact — FAIL CLOSED.

    Every failure mode is a :class:`CountersignError`: missing
    file, symlink, unparseable line, wrong header, broken hash
    chain, per-entry digest mismatch, tail digest mismatch, bad
    sequence, or zero receipt entries. There is no partial read.

    Raises:
        CountersignError: Any of the above.
    """
    raw, entries = _parse_artifact_lines(artifact_path)
    header = _validate_header(entries)

    prev = ""
    receipts: list[CheckReceipt] = []
    for n, entry in enumerate(entries):
        if entry.get("prev_digest") != prev:
            raise CountersignError(f"hash chain broken at entry {n}")
        if _entry_digest(entry) != entry.get("entry_digest"):
            raise CountersignError(f"entry digest mismatch at entry {n}")
        prev = str(entry["entry_digest"])
        if n > 0:
            receipts.append(_receipt_from_entry(entry, n))
    if not receipts:
        raise CountersignError("artifact carries no receipt entries")
    return ReceiptArtifact(
        path=artifact_path,
        commit=str(header.get("commit", "")),
        receipts=receipts,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def format_countersign_token(kind: str, seat: str, label: str, sha256: str) -> str:
    """Render the citable ledger token; round-trips the grammar.

    Raises:
        CountersignError: The rendered token does not match
            :data:`COUNTERSIGN_TOKEN_RE` (bad seat, label, or
            digest) — a token that the gate would flag is never
            produced in the first place.
    """
    token = f"{kind}: {seat} :: {label} :: sha256:{sha256[:16]}"
    if not COUNTERSIGN_TOKEN_RE.fullmatch(token):
        raise CountersignError(f"token does not match grammar: {token!r}")
    return token


def _format_receipts(receipts: Sequence[CheckReceipt]) -> str:
    blocks = []
    for r in receipts:
        status = "PASS" if r.passed else f"FAIL (exit {r.exit_code})"
        blocks.append(f"### {r.label}: {status}\n$ {shlex.join(r.argv)}\n{r.tail}")
    return "\n\n".join(blocks)


def build_countersign_brief(lead: str, artifact: ReceiptArtifact) -> str:
    """Build the seat brief MECHANICALLY from the verified artifact.

    No lead-authored text enters the brief — the evidence is the
    artifact's receipts, identified by commit and digest so the
    seat's verdict is anchored to auditable bytes.
    """
    return (
        "You are the rotating SKEPTIC seat at a three-model round "
        f"table. The LEAD ({lead}) re-ran delegated-lane receipts "
        "centrally; the append-only artifact below was written by "
        "the executing process and its digest chain verified. Judge "
        "ONLY from this evidence — do not run tools or invent "
        "checks that were not run.\n\n"
        f"Artifact sha256: {artifact.sha256}\n"
        f"Validated commit: {artifact.commit}\n\n"
        "Reply with EXACTLY one verdict block:\n\n"
        "VERDICT: COUNTERSIGN\n"
        "CITE: <label> :: <the command you weight most>\n\n"
        "or\n\n"
        "VERDICT: DISSENT\n"
        "CITE: <label> :: <the failing command>\n"
        "REASON: <one line, grounded in that command's output "
        "tail>\n\n"
        "Calibration: a countersign you did not check for is "
        "rubber-stamp decay; a failing receipt the lead's claim "
        "depends on earns a DISSENT. Text only.\n\n"
        f"## Re-run receipts (from artifact)\n{_format_receipts(artifact.receipts)}"
    )


def run_countersign_pass(
    artifact_path: Path,
    lead: str,
    board: object | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    seat_recipes: Sequence[tuple[str, tuple[str, ...]]] | None = None,
    prior_records: Sequence[Mapping[str, object]] = (),
    thread: str | None = None,
) -> CountersignPass:
    """Countersign the lead's receipt re-run from its artifact.

    Fail-closed: a token is emitted from exactly one path —
    digest-verified artifact + parsed COUNTERSIGN citing an
    executed receipt. Refusals (``no-artifact``, ``bad-artifact``,
    ``skeptic-absent``, ``malformed-verdict``) and DISSENT are
    recorded outcomes without a countersign token (a dissent gets
    a dissent token — equally citable, opposite meaning). Never
    flips a status, never promotes (R8).

    Raises:
        CountersignError: Unknown lead seat (caller error, not an
            artifact refusal).
    """
    from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

    if lead not in CANONICAL_SEATS:
        raise CountersignError(f"unknown lead seat: {lead!r}")
    invoke = invoke_seat or default_invoke_seat
    recipes = dict(seat_recipes or SEAT_RECIPES)
    record = CountersignPass(lead=lead)
    thread = thread or (f"countersign-{lead}-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}")

    try:
        artifact = load_receipt_artifact(artifact_path)
    except CountersignError as exc:
        record.outcome = "no-artifact" if not artifact_path.is_file() else "bad-artifact"
        _post(board, thread, "moderator", "halt", f"countersign refused: {exc}")
        return record
    record.artifact_sha256 = artifact.sha256
    record.receipts = list(artifact.receipts)

    brief = build_countersign_brief(lead, artifact)
    _post(board, thread, "moderator", "question", brief, countersign_for=lead)

    first = skeptic_for(lead, prior_records)
    start = CANONICAL_SEATS.index(first)
    ordered = [
        CANONICAL_SEATS[(start + i) % len(CANONICAL_SEATS)] for i in range(len(CANONICAL_SEATS))
    ]
    eligible = [seat for seat in ordered if seat != lead and seat in recipes]
    for seat in eligible[:2]:  # picked seat + one absent fallback
        code, reply = invoke(recipes[seat], brief)
        if code != 0 or not reply.strip():
            _post(
                board,
                thread,
                seat,
                "position",
                f"ABSENT — exit {code}: {reply[:200]}",
                absent=True,
                countersign_for=lead,
            )
            continue
        record.skeptic = seat
        record.verdict = parse_skeptic_verdict(
            reply, valid_labels=[r.label for r in artifact.receipts]
        )
        _post(board, thread, seat, "position", reply, countersign_for=lead)
        break

    if record.skeptic is None:
        record.outcome = "skeptic-absent"
        _post(
            board,
            thread,
            "moderator",
            "halt",
            f"no eligible skeptic seat reachable to countersign {lead!r}'s re-run",
        )
        return record

    verdict = record.verdict
    assert verdict is not None  # nosec B101 — set with record.skeptic above
    if verdict.kind in ("countersign", "dissent"):
        record.outcome = f"{verdict.kind}ed"
        label = (verdict.cite or "").split("::", 1)[0].strip()
        record.token = format_countersign_token(
            verdict.kind, record.skeptic, label, artifact.sha256
        )
    else:
        record.outcome = "malformed-verdict"

    _post(board, thread, "moderator", "synthesis", _digest(record), countersign_for=lead)
    return record


def _digest(record: CountersignPass) -> str:
    """Compact chair-facing summary of one countersign pass."""
    lines = [
        f"Countersign pass for lead {record.lead!r}: outcome={record.outcome}",
        f"skeptic={record.skeptic or 'ABSENT'} "
        f"artifact={record.artifact_sha256[:16] if record.artifact_sha256 else 'NONE'}",
        "receipts: "
        + "; ".join(
            f"{r.label}={'PASS' if r.passed else f'FAIL({r.exit_code})'}" for r in record.receipts
        ),
    ]
    if record.token:
        lines.append(f"ledger token: {record.token}")
    else:
        lines.append("NO ledger token (fail-closed refusal or malformed verdict)")
    lines.append("Chair rules; this pass never flips a status (R8).")
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
    """CLI for the two ends of the evidence path.

    ``rerun``: the executor end — re-run declared receipts and
    stream the artifact.  ``pass``: the skeptic end — verify the
    artifact and seek the countersign.  ``verify``: chair audit —
    verify a named artifact's chain and print its digest.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="D11c hardened countersign of lead receipt re-runs (R8: chair promotes)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_rerun = sub.add_parser("rerun", help="execute receipts, streaming the artifact")
    p_rerun.add_argument("artifact", help="artifact path to create (must not exist)")
    p_rerun.add_argument(
        "--check",
        action="append",
        required=True,
        metavar="LABEL::CMD",
        help="receipt as 'label :: command' (repeatable)",
    )
    p_rerun.add_argument("--repo", default=".")

    p_pass = sub.add_parser("pass", help="verify artifact and seek the countersign")
    p_pass.add_argument("artifact")
    p_pass.add_argument("--lead", required=True, choices=sorted(CANONICAL_SEATS))

    p_verify = sub.add_parser("verify", help="chair audit: verify chain, print digest")
    p_verify.add_argument("artifact")

    args = parser.parse_args(argv)
    artifact_path = Path(args.artifact)

    if args.command == "rerun":
        checks: list[tuple[str, list[str]]] = []
        for raw in args.check:
            label, sep, cmd = raw.partition("::")
            if not sep or not label.strip() or not cmd.strip():
                print(f"bad --check (want 'label :: command'): {raw!r}")
                return 2
            try:
                checks.append((label.strip(), shlex.split(cmd)))
            except ValueError as exc:
                print(f"unparseable command in {raw!r}: {exc}")
                return 2
        try:
            artifact = rerun_receipts_to_artifact(Path(args.repo).resolve(), checks, artifact_path)
        except (CountersignError, RuntimeError) as exc:
            print(f"countersign rerun: {exc}")
            return 2
        print(f"artifact written: {artifact.path} sha256:{artifact.sha256}")
        return 0

    if args.command == "verify":
        try:
            artifact = load_receipt_artifact(artifact_path)
        except CountersignError as exc:
            print(f"countersign verify: FAIL — {exc}")
            return 2
        print(f"artifact OK: {len(artifact.receipts)} receipt(s) sha256:{artifact.sha256}")
        return 0

    from attune.roundtable.board import Board

    try:
        record = run_countersign_pass(artifact_path, args.lead, board=Board())
    except CountersignError as exc:
        print(f"countersign: {exc}")
        return 2
    print(f"countersign pass complete: outcome={record.outcome}")
    if record.token:
        print(f"ledger token: {record.token}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
