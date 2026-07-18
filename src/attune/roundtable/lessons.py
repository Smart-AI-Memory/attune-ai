"""Lesson-candidate lane: structure, lint, and rendering (P2).

Implements the chair rulings on thread ``lessons-flow-001``
(``docs/specs/agent-round-table/decisions.md``, 2026-07-18):

- Lessons flow through a distinct promotion lane — the moderator
  drafts an atomic candidate, the chair approves per item.
- Candidates carry receipts from contact with the real system by
  default; the chair may waive for a strong design rationale, and a
  waived entry is visibly tagged as unverified.
- The mechanical gate this module is: **no receipt AND no waiver
  tag → blocked** before the candidate ever reaches the chair.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass

#: The visible marker a chair-waived (receipt-less) lesson carries,
#: verbatim from the ruling. Retrieval must be able to see which
#: entries never touched the real system.
WAIVER_TAG = "unverified — design rationale (chair-waived)"

#: Curation-bar bounds: candidates are atomic, not essays. A draft
#: that cannot fit is really several lessons, or a report.
TITLE_MAX_CHARS = 100
BODY_MAX_CHARS = 2000


@dataclass
class LessonCandidate:
    """One drafted lesson awaiting the chair's per-item review.

    Args:
        title: One-line bolded summary (the corpus's scan surface).
        body: The lesson itself — what to do or avoid, and why.
        evidence: The receipt: commands run, failure observed, diff
            that fixed it. Empty only when ``waived`` is True.
        waived: Chair-granted waiver for a design rationale that has
            not been exercised in code yet. Rendered with
            :data:`WAIVER_TAG`.
        thread: Board thread id the candidate came from (R10: the
            artifact records its origin).
    """

    title: str
    body: str
    evidence: str = ""
    waived: bool = False
    thread: str = ""

    def lint(self) -> list[str]:
        """Return the list of curation-bar violations (empty = clean).

        The blocking rule is the ruled one: a candidate with neither
        evidence nor a chair waiver never reaches the chair.
        """
        problems: list[str] = []
        title = self.title.strip()
        body = self.body.strip()
        if not title:
            problems.append("title is required")
        elif "\n" in title:
            problems.append("title must be a single line")
        elif len(title) > TITLE_MAX_CHARS:
            problems.append(f"title exceeds {TITLE_MAX_CHARS} chars — not scannable")
        if not body:
            problems.append("body is required")
        elif len(body) > BODY_MAX_CHARS:
            problems.append(
                f"body exceeds {BODY_MAX_CHARS} chars — split it or write a report instead"
            )
        if not self.evidence.strip() and not self.waived:
            problems.append(
                "BLOCKED: no receipt and no chair waiver — a candidate must "
                "carry evidence from the real system or an explicit "
                "chair-waived design rationale"
            )
        if self.evidence.strip() and self.waived:
            problems.append("carries evidence AND a waiver tag — drop the waiver")
        if not self.thread.strip():
            problems.append("thread id is required — the artifact records its origin")
        return problems

    def render(self) -> str:
        """Render the corpus-ready markdown entry.

        Raises:
            ValueError: If the candidate does not lint clean — only
                chair-approvable drafts are renderable.
        """
        problems = self.lint()
        if problems:
            raise ValueError("candidate does not lint clean: " + "; ".join(problems))
        tag = f" [{WAIVER_TAG}]" if self.waived else ""
        lines = [f"- **{self.title.strip()}**{tag}: {self.body.strip()}"]
        if self.evidence.strip():
            lines.append(f"  Evidence: {self.evidence.strip()}")
        lines.append(f"  (round-table thread {self.thread.strip()})")
        return "\n".join(lines)
