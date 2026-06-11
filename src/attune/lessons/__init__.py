"""Lessons corpus retrieval (lessons-corpus-rag T1).

Splits the repo's Lessons section (``## Lessons Learned`` in
``.claude/lessons.md``, falling back to ``.claude/CLAUDE.md`` until
the T5 cutover) into one retrievable document per top-level lesson,
plus one child document per bolded second-level bullet of the
consolidated mega-lessons (design D3 "atomic sub-splitting").

Retrieval rides attune-rag's shipped ``KeywordRetriever`` against an
in-memory corpus implementing ``CorpusProtocol`` with real
``RetrievalEntry`` instances (summary = the lesson title, which the
retriever weights 1.5x).

Usage::

    from attune.lessons import LessonsIndex

    index = LessonsIndex()  # auto-locates the lessons file
    for hit in index.retrieve("tag a release after squash merge"):
        print(hit.entry.summary, hit.score)

The index is mtime-cached: every ``entries()``/``retrieve()`` call
stats the file and rebuilds only when it changed (a rebuild on the
current ~380-lesson corpus is well under a second).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune_rag import RetrievalEntry, RetrievalHit

logger = logging.getLogger(__name__)

_LESSONS_HEADING = "## Lessons Learned"
_SUB_BULLET_RE = re.compile(r"^\s{2,}- \*\*")
_TITLE_RE = re.compile(r"- \*\*(.+?)\*\*")

__all__ = [
    "LessonsIndex",
    "find_lessons_file",
    "retrieve",
    "split_atomic",
    "split_lessons",
]


def find_lessons_file(start: Path | None = None) -> Path:
    """Locate the lessons corpus file by walking up from ``start``.

    Prefers ``.claude/lessons.md`` (the post-cutover home, design D3)
    over ``.claude/CLAUDE.md`` at each level.

    Args:
        start: Directory to begin the upward walk (default: cwd).

    Returns:
        Path to the first lessons file found.

    Raises:
        FileNotFoundError: If no candidate exists up to the
            filesystem root.
    """
    here = (start or Path.cwd()).resolve()
    for base in (here, *here.parents):
        for name in ("lessons.md", "CLAUDE.md"):
            candidate = base / ".claude" / name
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        f"no .claude/lessons.md or .claude/CLAUDE.md found walking up from {here}"
    )


def split_lessons(text: str) -> list[tuple[str, list[str]]]:
    """Split the Lessons section into ``(title, body_lines)`` docs.

    A lesson starts at a top-level ``- **`` bullet. Titles may wrap
    across lines (the file is wrapped at ~72 chars), so the title is
    extracted from the joined body, not the first line alone.
    """
    lessons_text = text[text.find(_LESSONS_HEADING) :]
    docs: list[list[str]] = []
    current: list[str] | None = None
    for ln in lessons_text.splitlines():
        if ln.startswith("- **"):
            if current:
                docs.append(current)
            current = [ln]
        elif ln.startswith("### ") or ln.startswith("## "):
            if current:
                docs.append(current)
            current = None
        elif current is not None:
            current.append(ln)
    if current:
        docs.append(current)

    out: list[tuple[str, list[str]]] = []
    for body in docs:
        joined = " ".join(line.strip() for line in body)
        m = _TITLE_RE.match(joined)
        title = (m.group(1) if m else joined[:80]).rstrip(": —")
        out.append((title, body))
    return out


def split_atomic(
    docs: list[tuple[str, list[str]]],
) -> list[tuple[str, list[str], int]]:
    """Generate child docs from mega-lessons' bolded sub-bullets (D3).

    A consolidated mega-lesson carries two or more second-level
    ``- **Title** — ...`` bullets, each a distinct lesson in its own
    right. Each becomes a child doc titled
    ``"<parent title> — <sub-bullet title>"`` so trap-moment queries
    can land on the specific sub-lesson instead of competing with the
    whole consolidated body.

    Plain (non-bolded) sub-bullets are ordinary list items, not
    atomic sub-lessons, and produce no children.

    Returns:
        ``(child_title, body_lines, parent_index)`` triples, where
        ``parent_index`` points into ``docs`` (children must stay
        linked to their lesson — retrieval dedups and the benchmark
        scores by parent).
    """
    children: list[tuple[str, list[str], int]] = []
    for parent_index, (title, body) in enumerate(docs):
        groups: list[list[str]] = []
        current: list[str] | None = None
        for ln in body:
            if _SUB_BULLET_RE.match(ln):
                if current:
                    groups.append(current)
                current = [ln]
            elif current is not None:
                if ln.startswith("- **"):
                    groups.append(current)
                    current = None
                else:
                    current.append(ln)
        if current:
            groups.append(current)
        if len(groups) < 2:
            continue
        for group in groups:
            joined = " ".join(line.strip() for line in group)
            m = _TITLE_RE.search(joined)
            head = (m.group(1) if m else joined[:60]).rstrip(": —")
            children.append((f"{title} — {head}", group, parent_index))
    return children


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70] or "lesson"


class LessonsIndex:
    """Mtime-cached retrieval index over the lessons corpus file.

    Implements attune-rag's ``CorpusProtocol`` (``entries()``,
    ``get()``, ``name``, ``version``) so it plugs straight into the
    shipped ``KeywordRetriever``.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        """Create an index over ``path`` (auto-located when None)."""
        self._path = Path(path) if path else find_lessons_file()
        self._stamp: tuple[int, int] | None = None
        self._entries: dict[str, Any] = {}

    @property
    def path(self) -> Path:
        """The lessons file backing this index."""
        return self._path

    @property
    def name(self) -> str:
        """Corpus name (CorpusProtocol)."""
        return "lessons"

    @property
    def version(self) -> str:
        """Corpus version: the backing file's mtime (CorpusProtocol)."""
        try:
            return str(self._path.stat().st_mtime_ns)
        except OSError:
            return "0"

    def entries(self) -> list[RetrievalEntry]:
        """All lesson entries, rebuilding from disk if the file changed."""
        self._refresh()
        return list(self._entries.values())

    def get(self, path: str) -> RetrievalEntry | None:
        """Look up one entry by its corpus path (CorpusProtocol)."""
        self._refresh()
        return self._entries.get(path)

    def retrieve(self, query: str, k: int = 3) -> list[RetrievalHit]:
        """Return the top-``k`` distinct lessons matching ``query``.

        Retrieves a larger candidate pool, then collapses child docs
        onto their lesson (highest-scored representative wins) so a
        mega-lesson's children can't crowd out other lessons from the
        top-``k``. A returned hit may be a child entry — its
        ``entry.metadata["parent_path"]`` names the lesson it belongs
        to.
        """
        from attune_rag import KeywordRetriever

        pool = KeywordRetriever().retrieve(query, self, k=max(k * 4, 12))
        out: list[RetrievalHit] = []
        seen: set[str] = set()
        for hit in pool:
            lesson = hit.entry.metadata.get("parent_path", hit.entry.path)
            if lesson in seen:
                continue
            seen.add(lesson)
            out.append(hit)
            if len(out) == k:
                break
        return out

    def _refresh(self) -> None:
        st = self._path.stat()
        stamp = (st.st_mtime_ns, st.st_size)
        if stamp == self._stamp:
            return
        from attune_rag import RetrievalEntry

        text = self._path.read_text(encoding="utf-8")
        parents = split_lessons(text)
        entries: dict[str, Any] = {}

        def _add(title: str, body: list[str], metadata: dict[str, Any]) -> str:
            slug = _slugify(title)
            base, n = slug, 2
            while f"{slug}.md" in entries:
                slug = f"{base}-{n}"
                n += 1
            rel = f"{slug}.md"
            entries[rel] = RetrievalEntry(
                path=rel,
                category="lesson",
                content="\n".join(body),
                summary=title,
                metadata=metadata,
            )
            return rel

        parent_rels = [_add(title, body, {}) for title, body in parents]
        for title, body, parent_index in split_atomic(parents):
            _add(title, body, {"parent_path": parent_rels[parent_index]})

        self._entries = entries
        self._stamp = stamp
        logger.debug("lessons index rebuilt: %d entries from %s", len(entries), self._path)


def retrieve(query: str, k: int = 3, path: Path | str | None = None) -> list[RetrievalHit]:
    """Convenience one-shot retrieval (builds a fresh index)."""
    return LessonsIndex(path).retrieve(query, k=k)
