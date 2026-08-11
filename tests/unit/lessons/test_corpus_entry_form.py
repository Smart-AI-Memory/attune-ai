# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Guard: every corpus lesson is a real entry, not swallowed prose.

``split_lessons`` anchors on RAW ``- **`` lines. A bolded-but-unbulleted
title does not open a new document — the splitter appends it to the
PRECEDING lesson's body, so it can never be the top hit for its own
topic and its title never surfaces.

Found 2026-08-11: 28 orphans in a 998-entry corpus. The pre-commit hook
(``check-lessons-corpus``) catches hand edits locally; this is the CI
half, because pre-commit can be skipped and never runs on a merge queue.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.check_lessons_corpus import CORPUS, find_orphans

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "check_lessons_corpus.py"


def test_corpus_has_no_orphan_entries():
    """The shipped corpus is clean. Fix: check_lessons_corpus.py --fix."""
    lines = CORPUS.read_text(encoding="utf-8").splitlines()
    orphans = find_orphans(lines)
    assert orphans == [], (
        f"{len(orphans)} bolded-but-unbulleted lesson entr"
        f"{'y' if len(orphans) == 1 else 'ies'} at line(s) "
        f"{[i + 1 for i in orphans]} — each is swallowed into the preceding "
        "lesson. Run: python scripts/check_lessons_corpus.py --fix"
    )


def test_guard_catches_a_planted_orphan(tmp_path: Path):
    """Load-bearing proof: the detector fires on a planted violation.

    Without this, a detector that silently matched nothing would keep
    the test above green forever.
    """
    corpus = tmp_path / "lessons.md"
    corpus.write_text(
        "## Lessons Learned\n\n- **Real entry**: body.\n\n**Orphan**: body.\n",
        encoding="utf-8",
    )
    lines = corpus.read_text(encoding="utf-8").splitlines()
    assert find_orphans(lines) == [4]

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--path", str(corpus)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Orphan" in result.stderr


def test_fix_prefixes_only_and_is_idempotent(tmp_path: Path):
    """--fix adds ``- `` and changes nothing else; re-running is a no-op."""
    corpus = tmp_path / "lessons.md"
    original = "## Lessons Learned\n\n- **Kept**: body.\n\n**Orphan**: body.\n"
    corpus.write_text(original, encoding="utf-8")

    for expected_rc, expected_tail in ((0, "- **Orphan**: body.\n"), (0, "- **Orphan**: body.\n")):
        rc = subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(corpus), "--fix"],
            capture_output=True,
            text=True,
        ).returncode
        assert rc == expected_rc
        text = corpus.read_text(encoding="utf-8")
        assert text.endswith(expected_tail)
        assert "- **Kept**: body." in text
        # Trailing newline preserved — splitlines()/join must not eat it.
        assert text.endswith("\n")


def test_mid_paragraph_bold_is_not_an_entry(tmp_path: Path):
    """A ``**`` line inside a paragraph is continuation prose, not a
    title — prefixing it would invent an entry and corrupt the body."""
    corpus = tmp_path / "lessons.md"
    corpus.write_text(
        "## Lessons Learned\n\n- **Real**: body line one\n**still the same paragraph**\n",
        encoding="utf-8",
    )
    assert find_orphans(corpus.read_text(encoding="utf-8").splitlines()) == []
