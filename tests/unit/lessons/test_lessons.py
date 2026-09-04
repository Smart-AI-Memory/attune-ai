"""Tests for ``attune.lessons`` (lessons-corpus-rag T1).

Covers the splitter (wrap-aware titles, counts on the real corpus),
atomic child-doc generation (D3), the mtime-cached ``LessonsIndex``,
parent-deduped retrieval, and a golden-query smoke subset.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.lessons import (
    LessonsIndex,
    find_lessons_file,
    retrieve,
    split_atomic,
    split_lessons,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_LESSONS = REPO_ROOT / ".claude" / "lessons.md"
FIXTURE = REPO_ROOT / "docs" / "specs" / "archive" / "lessons-corpus-rag" / "golden_queries.json"

SAMPLE = """\
# Header

## Lessons Learned

- **Short lesson title**: body line one
  continues on a second line.

- **A long lesson title that wraps across two physical lines because the
  file is wrapped at seventy-two characters**: the body starts here and
  keeps going.

- **Mega lesson about two related traps**:
  - **First trap** — details of the first trap, which has
    its own wrapped body.
  - **Second trap** — details of the second trap.

### A subsection heading

- **Lesson after a subsection**: still a lesson.
"""


class TestSplitLessons:
    def test_splits_top_level_bullets(self):
        docs = split_lessons(SAMPLE)
        assert len(docs) == 4

    def test_wrap_aware_title_extraction(self):
        docs = split_lessons(SAMPLE)
        titles = [t for t, _ in docs]
        assert (
            "A long lesson title that wraps across two physical lines because the"
            " file is wrapped at seventy-two characters" in titles
        )

    def test_title_strips_trailing_colon(self):
        docs = split_lessons(SAMPLE)
        assert docs[0][0] == "Short lesson title"
        assert not any(t.endswith(":") for t, _ in docs)

    def test_real_corpus_count_floor(self):
        # 375 measured at Phase 0 (2026-06-11); assert >=, not == —
        # the corpus grows with every session.
        docs = split_lessons(REAL_LESSONS.read_text(encoding="utf-8"))
        assert len(docs) >= 375

    def test_no_lessons_heading_yields_empty_or_all(self):
        # text.find() returns -1 -> whole text scanned; no top-level
        # bullets means no docs.
        assert split_lessons("# Nothing here\n\nplain text\n") == []


class TestSplitAtomic:
    def test_mega_lesson_yields_children_with_parent_index(self):
        docs = split_lessons(SAMPLE)
        children = split_atomic(docs)
        assert len(children) == 2
        titles = [t for t, _, _ in children]
        assert "Mega lesson about two related traps — First trap" in titles
        assert "Mega lesson about two related traps — Second trap" in titles
        mega_index = next(i for i, (t, _) in enumerate(docs) if t.startswith("Mega"))
        assert all(pi == mega_index for _, _, pi in children)

    def test_single_sub_bullet_produces_no_children(self):
        text = (
            "## Lessons Learned\n\n"
            "- **Parent**: intro\n"
            "  - **Only one bold sub-bullet** — not a mega lesson.\n"
        )
        assert split_atomic(split_lessons(text)) == []

    def test_stray_top_level_bullet_closes_group(self):
        # Direct-call contract: a column-0 "- **" line inside a body
        # (impossible via split_lessons, possible for direct callers)
        # closes the open sub-bullet group.
        body = [
            "- **T**:",
            "  - **A** — first.",
            "- **stray** top-level line",
            "  - **B** — second.",
        ]
        children = split_atomic([("T", body)])
        titles = [t for t, _, _ in children]
        assert titles == ["T — A", "T — B"]

    def test_plain_sub_bullets_produce_no_children(self):
        text = (
            "## Lessons Learned\n\n"
            "- **Parent**: intro\n"
            "  - plain list item one\n"
            "  - plain list item two\n"
        )
        assert split_atomic(split_lessons(text)) == []


class TestFindLessonsFile:
    def test_prefers_lessons_md_over_claude_md(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "CLAUDE.md").write_text("x", encoding="utf-8")
        (tmp_path / ".claude" / "lessons.md").write_text("y", encoding="utf-8")
        assert find_lessons_file(tmp_path).name == "lessons.md"

    def test_walks_up_to_parent(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        target = tmp_path / ".claude" / "CLAUDE.md"
        target.write_text("x", encoding="utf-8")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        assert find_lessons_file(nested) == target

    def test_raises_when_absent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_lessons_file(tmp_path)


def _write_lessons(path: Path, n: int = 2, mega: bool = False) -> None:
    parts = ["## Lessons Learned", ""]
    for i in range(n):
        parts.append(f"- **Lesson number {i} about topic{i}**: body for topic{i}.")
        parts.append("")
    if mega:
        parts += [
            "- **Mega lesson on deploy traps**:",
            "  - **Rollback trap** — always snapshot before rollback.",
            "  - **Cache trap** — bust the cache after deploy.",
            "",
        ]
    path.write_text("\n".join(parts), encoding="utf-8")


class TestLessonsIndex:
    def test_entries_and_protocol_surface(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=2)
        index = LessonsIndex(f)
        entries = index.entries()
        assert len(entries) == 2
        assert index.name == "lessons"
        assert index.version != "0"
        first = entries[0]
        assert index.get(first.path) is first
        assert index.get("nope.md") is None

    def test_children_carry_parent_path_metadata(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=1, mega=True)
        index = LessonsIndex(f)
        children = [e for e in index.entries() if "parent_path" in e.metadata]
        assert len(children) == 2
        parent_paths = {e.metadata["parent_path"] for e in children}
        assert parent_paths == {"mega-lesson-on-deploy-traps.md"}
        assert index.get("mega-lesson-on-deploy-traps.md") is not None

    def test_mtime_invalidation_rebuilds(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=2)
        index = LessonsIndex(f)
        assert len(index.entries()) == 2
        _write_lessons(f, n=3)
        assert len(index.entries()) == 3

    def test_cached_between_unchanged_reads(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=2)
        index = LessonsIndex(f)
        first = index.entries()
        second = index.entries()
        # Same objects -> no rebuild happened.
        assert first[0] is second[0]

    def test_retrieve_dedups_children_onto_lesson(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=1, mega=True)
        index = LessonsIndex(f)
        hits = index.retrieve("deploy rollback cache trap", k=3)
        lessons = [h.entry.metadata.get("parent_path", h.entry.path) for h in hits]
        assert len(lessons) == len(set(lessons)), "same lesson returned twice"

    def test_default_path_auto_located(self, tmp_path, monkeypatch):
        (tmp_path / ".claude").mkdir()
        f = tmp_path / ".claude" / "lessons.md"
        _write_lessons(f, n=1)
        monkeypatch.chdir(tmp_path)
        index = LessonsIndex()
        assert index.path == f

    def test_version_zero_when_file_unreadable(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=1)
        index = LessonsIndex(f)
        f.unlink()
        assert index.version == "0"

    def test_module_level_retrieve(self, tmp_path):
        f = tmp_path / "lessons.md"
        _write_lessons(f, n=2)
        hits = retrieve("topic0", path=f)
        assert hits
        assert hits[0].entry.summary == "Lesson number 0 about topic0"


class TestGoldenSmoke:
    """Retrieval smoke against 3 frozen golden queries (real corpus)."""

    @pytest.mark.parametrize(
        "query_id",
        [
            "pytest-cov-keyerror",
            pytest.param(
                "windows-crlf",
                marks=pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "corpus dilution at the 2026-09-04 outbox sweep (#2404): "
                        "the expected CRLF lesson scores 13.5 and sits at rank 4 "
                        "behind a new backend-import-contexts lesson at 14.0; "
                        "a keyword-precision fix should flip this back to XPASS "
                        "(strict) — chair-ruled xfail, not a fixture edit"
                    ),
                ),
            ),
            "tag-before-squash",
        ],
    )
    def test_golden_query_hits_top3(self, query_id):
        queries = json.loads(FIXTURE.read_text(encoding="utf-8"))["queries"]
        q = next(q for q in queries if q["id"] == query_id)
        index = LessonsIndex(REAL_LESSONS)
        hits = index.retrieve(q["query"], k=3)
        got = {Path(h.entry.metadata.get("parent_path", h.entry.path)).stem for h in hits}
        assert got & set(q["expected"]), f"{query_id}: top-3 missed, got {got}"
