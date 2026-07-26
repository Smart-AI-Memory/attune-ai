"""Notes search tool — the tutorial demo fixture.

A small, offline notes indexing and search module. This is DEMO DATA:
it exists so every attune-ai tutorial and dry run works on identical,
resettable material. Scoped via the dynamic-forms session on
2026-07-24 (resp-20260724-105201) and frozen that day.

Seeded on purpose (see README.md — do not "fix" these in cleanup PRs):

- One real bug that a test catches (the fix-test tutorial fixes it live).
- Several functions with no test coverage (the smart-test tutorial
  finds and closes them).

Runs fully offline on the stdlib. No real names, keys, or services.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: Words too common to be worth indexing.
STOP_WORDS = frozenset({"a", "an", "and", "in", "is", "of", "on", "the", "to"})


@dataclass
class Note:
    """One note: a title, a body, and optional tags."""

    note_id: int
    title: str
    body: str
    tags: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    """Split text into index tokens, dropping stop words.

    Tokens are matched case-insensitively by search().
    """
    # SEEDED BUG (fix-test tutorial): tokens keep their original case,
    # so "Redis" in a note never matches the lowercased query "redis".
    # The fix is one line: lowercase each token here.
    tokens = [t for t in re.split(r"[^\w]+", text) if t]
    return [t for t in tokens if t.lower() not in STOP_WORDS]


def load_notes(path: str | Path) -> list[Note]:
    """Load notes from a markdown-ish file.

    Format: notes separated by ``---`` lines; each note starts with a
    ``# title`` line, an optional ``tags: a, b`` line, then the body.

    Args:
        path: Path to the notes file. Must exist and be a regular file.

    Raises:
        FileNotFoundError: If the path does not name a regular file.
    """
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"notes file not found: {resolved}")

    notes: list[Note] = []
    for block in resolved.read_text(encoding="utf-8").split("\n---\n"):
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if not lines or not lines[0].startswith("# "):
            continue
        title = lines[0][2:].strip()
        tags: list[str] = []
        body_lines = lines[1:]
        if body_lines and body_lines[0].lower().startswith("tags:"):
            tags = [t.strip() for t in body_lines[0][5:].split(",") if t.strip()]
            body_lines = body_lines[1:]
        notes.append(
            Note(
                note_id=len(notes) + 1,
                title=title,
                body="\n".join(body_lines),
                tags=tags,
            )
        )
    return notes


class NotesIndex:
    """An in-memory inverted index over notes."""

    def __init__(self) -> None:
        self._notes: dict[int, Note] = {}
        self._index: dict[str, set[int]] = {}

    def add(self, note: Note) -> None:
        """Add one note to the index."""
        self._notes[note.note_id] = note
        for token in _tokenize(f"{note.title} {note.body}"):
            self._index.setdefault(token, set()).add(note.note_id)

    def add_all(self, notes: list[Note]) -> None:
        """Add many notes to the index."""
        for note in notes:
            self.add(note)

    def search(self, query: str) -> list[Note]:
        """Return notes matching the query, best match first.

        Matching is case-insensitive; ranking is by how many distinct
        query terms a note contains, ties broken by note id.
        """
        terms = [t.lower() for t in _tokenize(query)]
        if not terms:
            return []
        scores: dict[int, int] = {}
        for term in terms:
            for note_id in self._index.get(term, ()):
                scores[note_id] = scores.get(note_id, 0) + 1
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return [self._notes[note_id] for note_id, _ in ranked]

    def filter_by_tag(self, tag: str) -> list[Note]:
        """Return notes carrying the tag (case-insensitive), by id."""
        wanted = tag.strip().lower()
        found = [n for n in self._notes.values() if any(t.lower() == wanted for t in n.tags)]
        return sorted(found, key=lambda n: n.note_id)

    # -- Functions below are the seeded coverage gaps (smart-test
    # -- tutorial): correct, but no test exercises them yet.

    def remove(self, note_id: int) -> bool:
        """Remove a note; return True if it existed."""
        note = self._notes.pop(note_id, None)
        if note is None:
            return False
        for ids in self._index.values():
            ids.discard(note_id)
        self._index = {tok: ids for tok, ids in self._index.items() if ids}
        return True

    def snippet(self, note_id: int, width: int = 60) -> str:
        """Return the start of a note's body, cut at a word boundary."""
        note = self._notes.get(note_id)
        if note is None:
            return ""
        body = " ".join(note.body.split())
        if len(body) <= width:
            return body
        cut = body.rfind(" ", 0, width)
        return body[: cut if cut > 0 else width] + "…"

    def stats(self) -> dict[str, int]:
        """Return index size counters."""
        return {
            "notes": len(self._notes),
            "tokens": len(self._index),
            "tags": len({t.lower() for n in self._notes.values() for t in n.tags}),
        }
