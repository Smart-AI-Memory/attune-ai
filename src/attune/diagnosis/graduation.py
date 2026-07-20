"""Lesson graduation behind an interface (advanced-debugging-plugin
Phase D — dissent-register bound).

The corpus-ownership question (write to ``.claude/lessons.md`` direct
vs. a projected source) is UNRULED; until the chair rules, lesson
publication stays behind :class:`LessonPublisher`, and the ONLY v1
implementation renders the candidate for the chair — no file writes,
no corpus writes, anywhere.

Graduation gates (RR-7): a verification receipt on the diagnosis and
explicit chair approval; unverified or rejected diagnoses never
become lessons.
"""

from __future__ import annotations

from typing import Protocol

from attune.models.telemetry.data_models import DiagnosisRecord
from attune.roundtable.lessons import LessonCandidate


class GraduationError(ValueError):
    """The diagnosis is not eligible to graduate."""


class LessonPublisher(Protocol):
    """Where an approved lesson candidate goes — implementation TBD.

    The chair rules corpus ownership before any file-writing
    implementation exists; v1 ships only render-for-chair.
    """

    def publish(self, candidate: LessonCandidate) -> str:
        """Publish (or present) the candidate; returns a receipt string."""
        ...


class RenderForChairPublisher:
    """The v1 publisher: renders the linted candidate, writes nothing."""

    def publish(self, candidate: LessonCandidate) -> str:
        problems = candidate.lint()
        if problems:
            raise GraduationError("candidate fails lint: " + "; ".join(problems))
        return candidate.render()


def build_candidate(
    record: DiagnosisRecord, *, evidence: str, waived: bool = False
) -> LessonCandidate:
    """Build the lesson candidate from a VERIFIED diagnosis.

    Args:
        record: The diagnosis to graduate — ``status`` must be
            ``verified`` (the verification receipt gate).
        evidence: The receipt from the real system (commands run,
            failure observed, fixing diff) — transcript consensus
            never qualifies.
        waived: Chair-granted evidence waiver (never self-granted).
    """
    if record.status != "verified":
        raise GraduationError(
            f"diagnosis {record.diagnosis_id} is {record.status!r} — only "
            "verified diagnoses graduate"
        )
    top = record.hypotheses[0].statement if record.hypotheses else record.symptom
    return LessonCandidate(
        title=f"{record.workflow_name}: {record.symptom}"[:120],
        body=(f"Root cause: {top}. " f"{record.synthesis or ''}".strip()),
        evidence=evidence,
        waived=waived,
        thread=f"diagnosis:{record.diagnosis_id}",
    )


def graduate(
    record: DiagnosisRecord,
    *,
    evidence: str,
    waived: bool = False,
    publisher: LessonPublisher | None = None,
) -> str:
    """Graduate one verified diagnosis through the publisher interface."""
    candidate = build_candidate(record, evidence=evidence, waived=waived)
    return (publisher or RenderForChairPublisher()).publish(candidate)
