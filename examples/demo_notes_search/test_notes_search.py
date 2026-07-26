"""Tests for the notes-search demo fixture.

One test FAILS on purpose (the seeded tokenizer bug — the fix-test
tutorial fixes it live). The seeded coverage gaps are the functions
this file deliberately does not touch: remove(), snippet(), stats().

Run from this directory (or the repo root) with:
    pytest examples/demo_notes_search/test_notes_search.py -p no:cacheprovider -o addopts=
"""

from __future__ import annotations

from pathlib import Path

import pytest
from notes_search import Note, NotesIndex, load_notes

SAMPLE = Path(__file__).parent / "sample_notes.md"


@pytest.fixture()
def index() -> NotesIndex:
    idx = NotesIndex()
    idx.add_all(load_notes(SAMPLE))
    return idx


class TestLoadNotes:
    def test_loads_all_notes_with_titles(self) -> None:
        notes = load_notes(SAMPLE)
        assert len(notes) == 5
        assert notes[0].title == "Standup summary"
        assert notes[0].tags == ["work", "meetings"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_notes(tmp_path / "nope.md")


class TestSearch:
    def test_exact_case_match_found(self, index: NotesIndex) -> None:
        hits = index.search("coffee")
        assert [n.title for n in hits] == ["Grocery list"]

    def test_search_is_case_insensitive(self, index: NotesIndex) -> None:
        # "Redis" appears capitalized in the note body; a lowercase
        # query must still find it. (Fails until the tokenizer bug in
        # notes_search._tokenize is fixed.)
        hits = index.search("redis")
        assert [n.title for n in hits] == ["Standup summary"]

    def test_multi_term_ranking(self, index: NotesIndex) -> None:
        # "Workshop ideas" contains both terms; others contain one.
        hits = index.search("coverage testing")
        assert hits and hits[0].title == "Workshop ideas"

    def test_no_terms_returns_empty(self, index: NotesIndex) -> None:
        assert index.search("") == []
        assert index.search("the of and") == []


class TestTags:
    def test_filter_by_tag_case_insensitive(self, index: NotesIndex) -> None:
        titles = [n.title for n in index.filter_by_tag("WORK")]
        assert titles == ["Standup summary", "Workshop ideas"]

    def test_unknown_tag_empty(self, index: NotesIndex) -> None:
        assert index.filter_by_tag("nope") == []


class TestAdd:
    def test_added_note_is_searchable(self) -> None:
        idx = NotesIndex()
        idx.add(Note(note_id=1, title="Solo", body="a single searchable entry"))
        assert [n.title for n in idx.search("searchable")] == ["Solo"]
