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
from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat
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

_PROPOSER_BRIEF = """\
You are proposing a MINIMAL fix for a diagnosed workflow failure.
Reply with ONLY full-file blocks in exactly this format (one per
file, complete file contents, no prose outside the blocks):

--- file: <relative/path>
```
<complete file content>
```

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
) -> dict[str, Any]:
    """Run one propose→materialize→validate→review→discard cycle.

    Returns the ``proposed_fix`` dict for the DiagnosisRecord. Every
    disposition is explicit: ``below-threshold``, ``proposer-absent``,
    ``failed-materialize``, ``failed-validation``, ``proposed`` or
    ``rejected`` (reviewer verdicts). One repair round max.
    """
    config = config or DiagnosisConfig()
    if not confidence_meets_threshold(record, config):
        return {
            "disposition": "below-threshold",
            "threshold": config.fix_proposal_threshold,
        }

    proposer, proposer_recipe = seats[0]
    reviewer, reviewer_recipe = seats[1 % len(seats)]
    hypothesis = record.hypotheses[0].statement
    brief = _PROPOSER_BRIEF.format(
        synthesis=record.synthesis or record.symptom,
        hypothesis=hypothesis,
        repo=repo.name,
        repair="",
    )

    result: dict[str, Any] = {
        "proposer": proposer,
        "reviewer": reviewer,
        "repair_rounds": 0,
    }
    candidate: Candidate | None = None
    try:
        for attempt in range(2):  # initial + ONE repair round
            code, proposal = invoke_seat(proposer_recipe, brief)
            if code != 0 or not proposal.strip():
                result["disposition"] = "proposer-absent"
                result["detail"] = (proposal or "no reply")[-300:]
                return result
            try:
                candidate = materialize(proposal, repo)
            except (ProposalError, RuntimeError) as exc:
                if attempt == 0:
                    result["repair_rounds"] = 1
                    brief = _PROPOSER_BRIEF.format(
                        synthesis=record.synthesis or record.symptom,
                        hypothesis=hypothesis,
                        repo=repo.name,
                        repair=f"\nYour previous proposal failed: {exc}\nFix the format.",
                    )
                    continue
                result["disposition"] = "failed-materialize"
                result["detail"] = str(exc)[:300]
                return result
            break
        assert candidate is not None  # loop either set it or returned

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

        review_code, review = invoke_seat(
            reviewer_recipe,
            _REVIEWER_BRIEF.format(
                synthesis=record.synthesis or record.symptom,
                diff=diff[:DIFF_CHARS],
                receipts="\n".join(
                    f"[{c['label']}] exit {c['exit_code']}" for c in result["checks"]
                ),
            ),
        )
        verdict_line = next(
            (ln for ln in (review or "").splitlines() if ln.strip().upper().startswith("VERDICT")),
            "",
        )
        result["review"] = (review or "")[-600:] if review_code == 0 else "reviewer absent"
        approved = review_code == 0 and "APPROVE" in verdict_line.upper()
        result["disposition"] = "proposed" if approved else "rejected"
        return result
    finally:
        if candidate is not None:
            discard(candidate)
