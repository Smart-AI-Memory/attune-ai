"""Golden-query benchmark for the lessons-corpus-rag spec.

Scores the trap-moment queries in
``docs/specs/archive/lessons-corpus-rag/golden_queries.json`` against the
REAL ``attune.lessons.LessonsIndex`` (D6: the benchmark exercises the
shipped module — splitter, atomic child docs, parent-deduped
retrieval — not a harness-private corpus build).

Usage::

    .venv/bin/python scripts/phase0/lessons_rag_benchmark.py

Reports P@1 / P@3 overall and P@3 for the high-severity subset — the
inputs to the pre-committed go/no-go matrix in the spec's
``decisions.md`` (D1) and the T5 cutover gate (P@3 >= 80%, D6).
Scoring credits a hit on a child doc to its parent lesson (the
fixture's ``expected`` slugs are top-level lessons).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LESSONS_FILE = REPO_ROOT / ".claude" / "lessons.md"
FIXTURE = REPO_ROOT / "docs" / "specs" / "archive" / "lessons-corpus-rag" / "golden_queries.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from attune.lessons import LessonsIndex  # noqa: E402


def main() -> int:
    """Run the benchmark and print the matrix inputs."""
    index = LessonsIndex(LESSONS_FILE)
    entries = index.entries()
    parents = sum(1 for e in entries if "parent_path" not in e.metadata)
    print(f"corpus: {len(entries)} docs ({parents} lessons + {len(entries) - parents} children)")

    queries = json.loads(FIXTURE.read_text(encoding="utf-8"))["queries"]
    known = {Path(e.path).stem for e in entries}
    missing = [(q["id"], slug) for q in queries for slug in q["expected"] if slug not in known]
    if missing:
        print(f"MISSING expected slugs (fixture vs corpus drift): {missing}")
        return 1

    p1 = p3 = hs_total = hs_p3 = 0
    misses: list[str] = []
    for q in queries:
        hits = index.retrieve(q["query"], k=3)
        # Credit child-doc hits to their parent lesson.
        got = [Path(h.entry.metadata.get("parent_path", h.entry.path)).stem for h in hits]
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


if __name__ == "__main__":
    raise SystemExit(main())
