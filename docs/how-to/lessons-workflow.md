---
description: How the lessons loop works — where lessons live, how they come back, and the rule for adding new ones.
---

# Lessons Workflow

Attune AI keeps a corpus of engineering lessons and feeds them back
to you at the moment they apply. This page covers the loop: where
lessons live, how they're retrieved, and how to add one.

## Where lessons live

| File | Role |
|------|------|
| `.claude/lessons.md` | Canonical corpus — every lesson, full text |
| `.claude/CLAUDE.md` ("Lessons — core") | A small set of core lessons mirrored verbatim for always-in-context availability |

The split keeps session context lean (moving the corpus out of
CLAUDE.md cut it by 91%, freeing ~99k tokens per session) without
losing anything: the full corpus stays retrievable.

A drift-guard test (`tests/unit/lessons/test_core_mirror.py`)
asserts each core mirror byte-matches its canonical block in
lessons.md, so the two files cannot silently diverge.

## How lessons come back

Three retrieval surfaces, all reading `.claude/lessons.md`:

- **Prompt-time recall** — a `UserPromptSubmit` hook matches your
  prompt against the corpus and injects the top-matching lessons
  as context before the agent acts. Multi-part lessons are split
  into atomic sub-lessons so the specific gotcha surfaces, not
  just the umbrella title.
- **`/recall <topic>`** — on-demand search across both stores:
  past-session findings (file backend, or Redis Agent Memory
  Server when connected) and the lessons corpus.
- **Just-in-time rules** — a `PreToolUse` hook can attach a
  `lesson_ref` to a governing rule, resolved through
  `LessonsIndex` at fire time so the rule text stays current.

Programmatic access:

```python
from attune.lessons import LessonsIndex, find_lessons_file

index = LessonsIndex(find_lessons_file())
hits = index.retrieve("stash pop silently skipped files", k=3)
```

Retrieval quality on the project's golden-query benchmark:
P@1 84%, P@3 96%, with all high-severity queries hitting.

## Adding a lesson

1. Append the lesson to `.claude/lessons.md` under the
   `## Lessons Learned` heading (the splitter anchors on that
   literal heading). Use the existing format: a bold title bullet,
   then the body.
2. If the lesson is core-worthy (you want it in every session's
   context, not just retrieved on match), also mirror it verbatim
   into CLAUDE.md's `## Lessons — core` section. The drift guard
   enforces that the two copies match.

Do **not** append new lessons to CLAUDE.md alone — the canonical
home is lessons.md, and retrieval only sees what's there.
