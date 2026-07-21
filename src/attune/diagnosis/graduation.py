"""Lesson graduation behind an interface (advanced-debugging-plugin
Phase D).

Corpus ownership was chair-ruled 2026-07-20 (dissent register,
``docs/specs/advanced-debugging-plugin/decisions.md``): graduated
diagnostic lessons append DIRECTLY to ``.claude/lessons.md``,
chair-gated per entry, with the candidate's ``diagnosis:<id>`` thread
embedded inline as provenance so machine-graduated entries stay
distinguishable from session-written ones. :func:`graduate`'s default
remains render-for-chair; :class:`LessonsFilePublisher` is opt-in at
the call site (the chair-approval flow).

Graduation gates (RR-7): a verification receipt on the diagnosis and
explicit chair approval; unverified or rejected diagnoses never
become lessons.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Protocol

from attune.models.telemetry.data_models import DiagnosisRecord
from attune.roundtable.lessons import LessonCandidate
from attune.security.path_validation import _validate_file_path

#: Corpus wrap target — `.claude/lessons.md` entries are ~72-col.
_WRAP_WIDTH = 72


class GraduationError(ValueError):
    """The diagnosis is not eligible to graduate."""


class LessonPublisher(Protocol):
    """Where an approved lesson candidate goes.

    Two implementations: :class:`RenderForChairPublisher` (default —
    presents the entry, writes nothing) and
    :class:`LessonsFilePublisher` (chair-approved appends to the
    corpus, per the 2026-07-20 ruling).
    """

    def publish(self, candidate: LessonCandidate) -> str:
        """Publish (or present) the candidate; returns a receipt string."""
        ...


class RenderForChairPublisher:
    """The default publisher: renders the linted candidate, writes nothing."""

    def publish(self, candidate: LessonCandidate) -> str:
        problems = candidate.lint()
        if problems:
            raise GraduationError("candidate fails lint: " + "; ".join(problems))
        return candidate.render()


def _wrap_entry(rendered: str) -> str:
    """Re-wrap a rendered entry to the corpus's ~72-col convention.

    Each source line keeps its own leading indent; continuation lines
    take the corpus's two-space hanging indent. Long unbreakable
    tokens (ids, paths) are never split.
    """
    wrapped: list[str] = []
    for line in rendered.splitlines():
        indent = line[: len(line) - len(line.lstrip(" "))]
        wrapped.append(
            textwrap.fill(
                line.strip(),
                width=_WRAP_WIDTH,
                initial_indent=indent,
                subsequent_indent="  ",
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(wrapped)


class LessonsFilePublisher:
    """Chair-approved publisher: appends the entry to ``.claude/lessons.md``.

    Per the 2026-07-20 corpus-ownership ruling. The candidate's
    ``diagnosis:<id>`` thread is embedded in the rendered entry (via
    :meth:`LessonCandidate.render`) as machine-graduation provenance.

    Duplicate policy (documented decision): re-publishing a diagnosis
    whose thread marker already appears in the corpus is receipted as
    **already-published** — an idempotent no-op, not an error. The
    chair-approval flow may be retried after an interruption, and a
    duplicate append would double the corpus entry while an exception
    would fail loudly on a state that is actually success.

    Args:
        lessons_path: Corpus file; defaults to
            ``<project_root>/.claude/lessons.md``.
        project_root: Directory writes are restricted to; defaults to
            the current working directory. The resolved path is
            validated against it (CWE-22 guard).

    Raises:
        ValueError: If the resolved path escapes ``project_root`` or
            is otherwise unsafe.
    """

    def __init__(
        self,
        lessons_path: str | Path | None = None,
        *,
        project_root: str | Path | None = None,
    ) -> None:
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        target = Path(lessons_path) if lessons_path else root / ".claude" / "lessons.md"
        if not target.is_absolute():
            target = root / target
        self._path = _validate_file_path(str(target), allowed_dir=str(root))

    def publish(self, candidate: LessonCandidate) -> str:
        problems = candidate.lint()
        if problems:
            raise GraduationError("candidate fails lint: " + "; ".join(problems))
        # The rendered provenance line ends "thread <id>)" — matching on
        # that suffix keeps diagnosis:d1 from false-matching diagnosis:d12.
        marker = f"thread {candidate.thread.strip()})"
        existing = self._path.read_text(encoding="utf-8") if self._path.exists() else ""
        title = candidate.title.strip()
        if marker in existing:
            return (
                f"already published: {self._path} carries an entry for "
                f"{candidate.thread.strip()} — nothing appended"
            )
        entry = _wrap_entry(candidate.render())
        with self._path.open("a", encoding="utf-8") as fh:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            if existing:
                fh.write("\n")
            fh.write(entry + "\n")
        return f"appended to {self._path}: {title}"


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
