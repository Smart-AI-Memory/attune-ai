"""Propose-only fix loop (advanced-debugging-plugin RR-6, Phase D T6).

Binds the shipped solutions lifecycle — materialize in a scratch
worktree, validate with receipted checks, DIFFERENT-seat review,
unconditional discard — behind the confidence threshold gate. The
user's working tree is never touched; failed validation stays visible
(TAC-4); the scratch worktree is discarded in ``finally``.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from attune.models.telemetry.data_models import DiagnosisRecord
from attune.roundtable.routine import PLAN_ONLY_SEATS, SEAT_RECIPES, default_invoke_seat
from attune.roundtable.solutions import (
    Candidate,
    ProposalError,
    diff_against_base,
    discard,
    materialize,
    validate,
)

from .config import DiagnosisConfig

logger = logging.getLogger(__name__)

#: Max chars of diff carried into ``proposed_fix`` (the full diff lives
#: only in the chair-facing presentation; the record stays bounded).
DIFF_CHARS = 8_000

#: Literal worked example of a file block. Prose alone was not enough:
#: live-fire 2 (advanced-debugging-plugin decisions.md, 2026-07-20) had
#: codex answer BOTH rounds with diff/prose interleaving that
#: materialized to nothing — the producing-run precedent
#: (``producing.TAG_EXAMPLE``) is a literal shape to copy.
FILE_BLOCK_EXAMPLE = """\
EXAMPLE REPLY (copy this shape exactly — a '--- file:' line, then a
fenced block holding the COMPLETE new file content; nothing else):

--- file: src/example/target.py
```
VALUE = 2
```"""

_PROPOSER_BRIEF = """\
You are proposing a MINIMAL fix for a diagnosed workflow failure.
Reply with ONLY full-file blocks in exactly this format (one per
file, complete file contents, no prose outside the blocks — do NOT
send a unified diff, an explanation, or partial snippets):

--- file: <relative/path>
```
<complete file content>
```

{example}

Diagnosis:
{synthesis}

Top hypothesis: {hypothesis}
Repository: {repo}
{repair}
"""

_REVIEWER_BRIEF = """\
You are reviewing another seat's proposed fix. You did NOT write it.
Reply with exactly one line starting with VERDICT: APPROVE or
VERDICT: REJECT, then a short rationale.

Diagnosis synthesis:
{synthesis}

Proposed diff:
{diff}

Check receipts:
{receipts}
"""


def confidence_meets_threshold(record: DiagnosisRecord, config: DiagnosisConfig) -> bool:
    """True when the top hypothesis clears ``fix_proposal_threshold``."""
    if not record.hypotheses:
        return False
    scale = list(config.confidence_scale)
    top = record.hypotheses[0].confidence
    try:
        return scale.index(top) >= scale.index(config.fix_proposal_threshold)
    except ValueError:
        return False


def _default_checks(candidate: Candidate) -> list[tuple[str, list[str]]]:
    """Minimal always-available check: the touched files still compile."""
    py_files = [f for f in candidate.files if f.endswith(".py")]
    if not py_files:
        return []
    return [("py-compile", [sys.executable, "-m", "py_compile", *py_files])]


def run_fix_loop(
    record: DiagnosisRecord,
    repo: Path,
    config: DiagnosisConfig | None = None,
    *,
    seats: Sequence[tuple[str, tuple[str, ...]]] = SEAT_RECIPES,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] = default_invoke_seat,
    checks: list[tuple[str, list[str]]] | None = None,
    plan_only: frozenset[str] = PLAN_ONLY_SEATS,
) -> dict[str, Any]:
    """Run one propose→materialize→validate→review→discard cycle.

    Returns the ``proposed_fix`` dict for the DiagnosisRecord. Every
    disposition is explicit: ``below-threshold``,
    ``no-code-emitting-proposer``, ``proposer-absent``,
    ``failed-materialize``, ``failed-validation``, ``proposed`` or
    ``rejected`` (reviewer verdicts). One repair round max.

    Role fit (v1.1): the proposer must be a CODE-EMITTING seat —
    seats named in ``plan_only`` never propose (they may review).
    When a proposer is absent, the next code-emitting seat takes
    over and absent seats are skipped for review too (live-fire
    precedent: claude absent → codex proposed, antigravity
    reviewed).
    """
    config = config or DiagnosisConfig()
    if not confidence_meets_threshold(record, config):
        return {
            "disposition": "below-threshold",
            "threshold": config.fix_proposal_threshold,
        }

    proposers = [(name, recipe) for name, recipe in seats if name not in plan_only]
    if not proposers:
        return {
            "disposition": "no-code-emitting-proposer",
            "detail": "every roster seat is plan-only; code-native seats propose",
        }

    result: dict[str, Any] = {"repair_rounds": 0, "absent_proposers": []}
    candidate: Candidate | None = None
    try:
        for proposer, proposer_recipe in proposers:
            result["proposer"] = proposer
            result.pop("detail", None)  # a prior absent seat's detail is stale
            candidate = _propose_candidate(record, repo, proposer_recipe, invoke_seat, result)
            if candidate is not None or result["disposition"] != "proposer-absent":
                break  # proposed, or a terminal format failure — never seat-shop those
            result["absent_proposers"].append(proposer)
        if candidate is None:
            return result  # disposition already set by the propose step

        candidate = validate(candidate, checks or _default_checks(candidate))
        result["checks"] = [
            {"label": r.label, "exit_code": r.exit_code, "tail": r.tail} for r in candidate.receipts
        ]
        diff = diff_against_base(candidate, repo)
        result["diff"] = diff[:DIFF_CHARS]
        result["files"] = list(candidate.files)
        if not candidate.green:
            # Failed validation stays VISIBLE — never laundered green.
            result["disposition"] = "failed-validation"
            return result

        reviewer = _pick_reviewer(seats, result["proposer"], result["absent_proposers"])
        if reviewer is None:
            # Never launder an unreviewed candidate to "proposed".
            result["reviewer"] = None
            result["review"] = "no distinct reviewer available"
            result["disposition"] = "rejected"
            return result
        result["reviewer"] = reviewer[0]
        _review_candidate(record, diff, reviewer[1], invoke_seat, result)
        return result
    finally:
        if candidate is not None:
            discard(candidate)


def _propose_candidate(
    record: DiagnosisRecord,
    repo: Path,
    proposer_recipe: tuple[str, ...],
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]],
    result: dict[str, Any],
) -> Candidate | None:
    """Invoke the proposer and materialize, with ONE repair round.

    Returns the candidate, or ``None`` after setting the terminal
    disposition (``proposer-absent`` / ``failed-materialize``) on
    ``result``.
    """
    hypothesis = record.hypotheses[0].statement
    brief = _PROPOSER_BRIEF.format(
        example=FILE_BLOCK_EXAMPLE,
        synthesis=record.synthesis or record.symptom,
        hypothesis=hypothesis,
        repo=repo.name,
        repair="",
    )
    for attempt in range(2):  # initial + ONE repair round
        code, proposal = invoke_seat(proposer_recipe, brief)
        if code != 0 or not proposal.strip():
            result["disposition"] = "proposer-absent"
            result["detail"] = (proposal or "no reply")[-300:]
            return None
        try:
            return materialize(proposal, repo)
        except (ProposalError, RuntimeError) as exc:
            if attempt == 0:
                result["repair_rounds"] = 1
                # Name the failure AND restate the contract: the old
                # "unified diff names no target files / fix the format"
                # message steered seats TOWARD unified diffs (live-fire
                # 2 — codex stayed dirty through its repair round).
                brief = _PROPOSER_BRIEF.format(
                    example=FILE_BLOCK_EXAMPLE,
                    synthesis=record.synthesis or record.symptom,
                    hypothesis=hypothesis,
                    repo=repo.name,
                    repair=(
                        f"\nYour previous reply could not be materialized: {exc}\n"
                        "Resend the COMPLETE fix as '--- file:' blocks in the "
                        "EXAMPLE shape above — full file contents, no prose, "
                        "no unified diff."
                    ),
                )
                continue
            result["disposition"] = "failed-materialize"
            result["detail"] = str(exc)[:300]
            return None
    return None  # unreachable — loop returns on every path


def _pick_reviewer(
    seats: Sequence[tuple[str, tuple[str, ...]]],
    proposer: str,
    absent: Sequence[str],
) -> tuple[str, tuple[str, ...]] | None:
    """First roster seat that differs from the proposer and is not
    known-absent — plan-only seats review fine. None when the roster
    has no such seat.
    """
    for name, recipe in seats:
        if name != proposer and name not in absent:
            return name, recipe
    return None


def _review_candidate(
    record: DiagnosisRecord,
    diff: str,
    reviewer_recipe: tuple[str, ...],
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]],
    result: dict[str, Any],
) -> None:
    """Different-seat review; sets ``proposed`` / ``rejected`` on result."""
    review_code, review = invoke_seat(
        reviewer_recipe,
        _REVIEWER_BRIEF.format(
            synthesis=record.synthesis or record.symptom,
            diff=diff[:DIFF_CHARS],
            receipts="\n".join(f"[{c['label']}] exit {c['exit_code']}" for c in result["checks"]),
        ),
    )
    verdict_line = next(
        (ln for ln in (review or "").splitlines() if ln.strip().upper().startswith("VERDICT")),
        "",
    )
    result["review"] = (review or "")[-600:] if review_code == 0 else "reviewer absent"
    approved = review_code == 0 and "APPROVE" in verdict_line.upper()
    result["disposition"] = "proposed" if approved else "rejected"
