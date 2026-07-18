"""Lesson-candidate lane tests (agent-round-table Phase 2).

The lint is the chair-ruled mechanical gate (thread
lessons-flow-001): no receipt AND no waiver tag → blocked before
the candidate reaches the chair. Pure logic — no Redis needed.
"""

from __future__ import annotations

import pytest

from attune.roundtable import WAIVER_TAG, LessonCandidate


def _receipted(**overrides) -> LessonCandidate:
    fields = {
        "title": "codex exec blocks on non-TTY stdin",
        "body": "Use `codex exec -` with the brief on stdin.",
        "evidence": "hung 2026-07-18, ~0 CPU; `codex exec -` returned in 10s",
        "thread": "lessons-flow-001",
    }
    fields.update(overrides)
    return LessonCandidate(**fields)


class TestBlockingRule:
    def test_receipted_candidate_lints_clean(self) -> None:
        assert _receipted().lint() == []

    def test_no_receipt_no_waiver_is_blocked(self) -> None:
        problems = _receipted(evidence="").lint()
        assert any(p.startswith("BLOCKED") for p in problems)

    def test_waiver_substitutes_for_receipt(self) -> None:
        assert _receipted(evidence="", waived=True).lint() == []

    def test_evidence_plus_waiver_is_flagged(self) -> None:
        problems = _receipted(waived=True).lint()
        assert problems == ["carries evidence AND a waiver tag — drop the waiver"]

    def test_whitespace_evidence_is_no_receipt(self) -> None:
        problems = _receipted(evidence="   \n ").lint()
        assert any(p.startswith("BLOCKED") for p in problems)


class TestCurationBar:
    def test_missing_title_body_thread(self) -> None:
        problems = LessonCandidate(title="", body="").lint()
        assert "title is required" in problems
        assert "body is required" in problems
        assert any("thread id is required" in p for p in problems)

    def test_multiline_title_rejected(self) -> None:
        assert "title must be a single line" in _receipted(title="a\nb").lint()

    def test_oversize_title_and_body_rejected(self) -> None:
        problems = _receipted(title="t" * 101, body="b" * 2001).lint()
        assert any("title exceeds" in p for p in problems)
        assert any("body exceeds" in p for p in problems)


class TestRender:
    def test_blocked_candidate_refuses_to_render(self) -> None:
        with pytest.raises(ValueError, match="does not lint clean"):
            _receipted(evidence="").render()

    def test_receipted_render_carries_evidence_and_thread(self) -> None:
        entry = _receipted().render()
        assert entry.startswith("- **codex exec blocks on non-TTY stdin**: ")
        assert "  Evidence: hung 2026-07-18" in entry
        assert "(round-table thread lessons-flow-001)" in entry
        assert WAIVER_TAG not in entry

    def test_waived_render_carries_the_visible_tag(self) -> None:
        entry = _receipted(evidence="", waived=True).render()
        assert f"[{WAIVER_TAG}]" in entry
        assert "Evidence:" not in entry
