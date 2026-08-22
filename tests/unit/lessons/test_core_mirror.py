"""Drift guard: CLAUDE.md's "Lessons — core" mirrors lessons.md.

The T5 cutover (docs/specs/lessons-corpus-rag/) keeps ~20
always-loaded core lessons in .claude/CLAUDE.md as VERBATIM mirrors
of entries in .claude/lessons.md (the canonical corpus). This guard
fails when a mirror diverges — the fix is to re-sync the core copy
from (or to) its lessons.md canon, editing BOTH files.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path

import pytest

lessons_mod = pytest.importorskip("attune.lessons")

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_MD = REPO_ROOT / ".claude" / "CLAUDE.md"
LESSONS_MD = REPO_ROOT / ".claude" / "lessons.md"

CORE_HEADING = "## Lessons — core"

# Hard ceiling for the always-loaded core section, in bytes. Core is the
# single largest eagerly-loaded block in the repo — it dwarfs the 20,000
# byte budget that tests/unit/rules/test_rules_residency_budget.py pins on
# eager rules, yet was governed only by an entry COUNT until 2026-08-22.
# A count cap is a poor ceiling: at the observed ~1,690 B/entry mean, the
# <= 30 cap silently authorises ~51 KB nobody ratified. This budget binds
# BEFORE the count cap, so a promotion that costs real context trips here
# and forces the eviction conversation. Seeded at 44,951 (26 entries,
# 2026-08-22). SHRINK-ONLY: demote something rather than widening it.
CORE_BUDGET_BYTES = 46_000


def _core_section_text() -> str:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert CORE_HEADING in text, "core section missing from CLAUDE.md"
    section = text.split(CORE_HEADING, 1)[1]
    # core runs to the next ## heading or EOF
    for line in section.splitlines():
        if line.startswith("## "):
            section = section.split("\n" + line, 1)[0]
            break
    return section


def _top_level_lessons(text: str) -> dict[str, str]:
    """title -> normalized body for each top-level lesson in ``text``."""
    # split_lessons anchors on the canonical section heading; the core
    # section uses a different one, so prepend the anchor when absent.
    if "## Lessons Learned" not in text:
        text = "## Lessons Learned\n" + text
    parents = lessons_mod.split_lessons(text)
    return {title: "\n".join(body).strip() for title, body in parents}


def test_every_core_lesson_mirrors_lessons_md_verbatim() -> None:
    core = _top_level_lessons(_core_section_text())
    canon = _top_level_lessons(LESSONS_MD.read_text(encoding="utf-8"))
    assert 15 <= len(core) <= 30, f"core size {len(core)} outside the ~20 cap"
    for title, body in core.items():
        assert title in canon, (
            f"core lesson {title[:60]!r} has no canon entry in lessons.md "
            "(title edited in one file only?)"
        )
        assert body == canon[title], (
            f"core lesson {title[:60]!r} DIVERGED from its lessons.md canon "
            "— re-sync both copies"
        )


def test_core_section_within_byte_budget() -> None:
    """The always-loaded core stays under its context budget."""
    total = len(_core_section_text().encode("utf-8"))
    assert total <= CORE_BUDGET_BYTES, (
        f"core section is {total:,} bytes > {CORE_BUDGET_BYTES:,} budget — "
        "demote a core lesson to the lessons.md tail rather than widening "
        "the budget (it is shrink-only). Core is always-loaded context."
    )


def test_lessons_md_is_the_index_source() -> None:
    """find_lessons_file must prefer lessons.md now that it exists."""
    found = lessons_mod.find_lessons_file(REPO_ROOT)
    assert found == LESSONS_MD


def test_corpus_did_not_shrink() -> None:
    canon = _top_level_lessons(LESSONS_MD.read_text(encoding="utf-8"))
    assert len(canon) >= 380, f"corpus has {len(canon)} lessons — lost content?"
