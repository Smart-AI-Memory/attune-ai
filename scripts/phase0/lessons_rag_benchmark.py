"""Phase 0 benchmark for the lessons-corpus-rag spec.

Splits the ``.claude/CLAUDE.md`` Lessons section into one document per
top-level lesson, builds an attune-rag ``DirectoryCorpus`` (summary =
the lesson's bold title), and scores the golden trap-moment queries in
``docs/specs/lessons-corpus-rag/golden_queries.json`` with the shipped
``KeywordRetriever``.

Usage::

    .venv/bin/python scripts/phase0/lessons_rag_benchmark.py

Reports P@1 / P@3 overall and P@3 for the high-severity subset — the
inputs to the pre-committed go/no-go matrix in the spec's
``decisions.md`` (D1). Re-run whenever the corpus split strategy or
retriever changes; the fixture stays frozen.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LESSONS_FILE = REPO_ROOT / ".claude" / "CLAUDE.md"
FIXTURE = REPO_ROOT / "docs" / "specs" / "lessons-corpus-rag" / "golden_queries.json"


def split_lessons(text: str) -> list[tuple[str, list[str]]]:
    """Split the Lessons section into ``(title, body_lines)`` docs.

    A lesson starts at a top-level ``- **`` bullet. Titles may wrap
    across lines (the file is wrapped at ~72 chars), so the title is
    extracted from the joined body, not the first line alone.
    """
    lessons_text = text[text.find("## Lessons Learned") :]
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
        m = re.match(r"- \*\*(.+?)\*\*", joined)
        title = (m.group(1) if m else joined[:80]).rstrip(": —")
        out.append((title, body))
    return out


def build_corpus_dir(docs: list[tuple[str, list[str]]], root: Path) -> dict[str, str]:
    """Write one markdown file per lesson; return path → title summaries."""
    summaries: dict[str, str] = {}
    seen: set[str] = set()
    for title, body in docs:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70] or "lesson"
        base, n = slug, 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen.add(slug)
        rel = f"{slug}.md"
        (root / rel).write_text(f"# {title}\n\n" + "\n".join(body) + "\n", encoding="utf-8")
        summaries[rel] = title
    return summaries


def main() -> int:
    """Run the benchmark and print the matrix inputs."""
    from attune_rag import DirectoryCorpus, KeywordRetriever

    text = LESSONS_FILE.read_text(encoding="utf-8")
    docs = split_lessons(text)

    tmp = Path(tempfile.mkdtemp(prefix="lessons-rag-"))
    try:
        summaries = build_corpus_dir(docs, tmp)
        corpus = DirectoryCorpus(tmp, extra_summaries=summaries)
        entries = list(corpus.entries())
        with_summary = sum(1 for e in entries if getattr(e, "summary", None))
        print(f"corpus: {len(entries)} lessons, {with_summary} with summaries")
        if with_summary != len(entries):
            print("WARNING: summaries not reaching the retriever — fix before scoring")

        queries = json.loads(FIXTURE.read_text(encoding="utf-8"))["queries"]
        missing = [
            (q["id"], slug)
            for q in queries
            for slug in q["expected"]
            if not (tmp / f"{slug}.md").is_file()
        ]
        if missing:
            print(f"MISSING expected slugs (fixture vs corpus drift): {missing}")
            return 1

        retriever = KeywordRetriever()
        p1 = p3 = hs_total = hs_p3 = 0
        misses: list[str] = []
        for q in queries:
            hits = retriever.retrieve(q["query"], corpus, k=3)
            got = [Path(h.entry.path).stem for h in hits]
            expected = set(q["expected"])
            hit1 = bool(got) and got[0] in expected
            hit3 = any(g in expected for g in got)
            p1 += hit1
            p3 += hit3
            if q["severity"] == "high":
                hs_total += 1
                hs_p3 += hit3
            if not hit3:
                misses.append(f"  {q['id']} -> {[g[:45] for g in got]}")

        n = len(queries)
        print(f"P@1: {p1}/{n} = {p1 / n:.0%}")
        print(f"P@3: {p3}/{n} = {p3 / n:.0%}")
        print(f"high-severity P@3: {hs_p3}/{hs_total}")
        if misses:
            print("misses:")
            print("\n".join(misses))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
