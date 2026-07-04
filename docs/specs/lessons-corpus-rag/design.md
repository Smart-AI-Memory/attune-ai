# Lessons Corpus via RAG — Design
**Status:** approved (2026-06-11) — authored after Phase 0 GO (D2).
Grounded in the measured numbers: 375 lessons / ~116k tokens / 58%
of window; keyword P@3 84%, high-severity 7/7.

## D3 — Store shape: a sibling file, not a database

The lessons move from `.claude/CLAUDE.md` to **`.claude/lessons.md`**
— same format, same repo, same git history, just NOT auto-loaded
(Claude Code loads `CLAUDE.md` + its `@`-imports only; `lessons.md`
is deliberately not imported).

- **One write path (R3) preserved exactly:** appending a lesson is
  still "edit one markdown file"; the format is unchanged (top-level
  `- **title**:` bullets). No database, no ingest job, no sync.
- **Retrieval is split-on-read:** consumers call a shared
  `attune.lessons` module that reads `lessons.md`, splits it with the
  wrap-aware splitter (proven in `scripts/phase0/
  lessons_rag_benchmark.py`), and builds an in-memory
  `DirectoryCorpus`-equivalent keyed by mtime — a cache rebuild costs
  well under a second for 375 docs, so freshness is automatic.
- **Atomic sub-splitting at ingest (D2 carry-forward):** consolidated
  mega-lessons (multi-bullet bodies) additionally index each
  second-level bullet as a child doc titled
  `"<parent title> — <sub-bullet head>"`. Fixes 2 of the 4 Phase 0
  misses without touching the authoring format.
- **Reversibility (R5):** the cutover is one `git mv`-shaped edit;
  reverting is the same edit backwards.

Rejected: AMS/Redis store (adds a service dependency to something
that must work in every fresh clone); per-lesson files on disk
(makes authoring N-file instead of 1-file, violating R3).

## D4 — The always-loaded core (R2)

A `## Lessons — core` section stays in `.claude/CLAUDE.md`, capped at
~20 entries. Selection criteria, in priority order:

1. **All high-severity classes** (secret exposure, lost work / broken
   main, real money) — this makes R4's high-severity gate structural:
   those lessons never depend on retrieval.
2. **Session-mechanics lessons that fire before any retrieval could**
   (worktree paths, branch-vs-worktree commits, commit hygiene) —
   needed during the very actions that would query the store.
3. **Highest observed fire-frequency** (judgment, reviewed by
   Patrick at cutover).

The core section ends with a pointer paragraph: where the tail
lives, how to query it (`/recall <topic>`), and the instruction to
append new lessons to `lessons.md`.

## D5 — Retrieval surfaces (three, sharing one module)

`src/attune/lessons/` (new, small): `split_lessons()`,
`LessonsIndex` (mtime-cached), `retrieve(query, k=3) -> hits`.
The Phase 0 harness's splitter moves here and the harness imports it
(single source of truth; the benchmark becomes the module's
regression test).

1. **`/recall` skill** — extended to query the lessons index
   alongside the AMS session-findings store it already reads.
   On-demand, transparent, the solo-dev-preferred surface
   (cross-session-memory D1 precedent).
2. **UserPromptSubmit hook** — the automatic surface. On each user
   prompt: retrieve top-3 lessons scoring above a floor against the
   prompt text; inject matched titles + bodies (truncated) via
   `additionalContext` (channel verified — same mechanism as
   jit-recall's PreToolUse, documented as working for
   UserPromptSubmit). Noise controls: surface-once per (session,
   lesson) sentinel, score floor so most prompts inject nothing,
   `ATTUNE_LESSON_RECALL=0` off-switch, fail-safe exit 0 — the
   established hook conventions.
3. **jit-recall map entries** — `_recall_map.py` entries gain an
   optional `lesson_ref` (slug) resolved through the index at fire
   time, replacing inline rule text where a lesson is the source.
   Keeps the curated-map precision for decision-point timing.

## D6 — R4 behavioral gate at cutover

- High-severity lessons live in the core (D4) — structurally exempt
  from retrieval risk.
- The golden benchmark re-runs against the REAL `lessons.md` +
  `attune.lessons` index (not the harness's own split) and must hold
  P@3 ≥ 80%; the benchmark gains the atomic-split child docs, so the
  two split-related misses are expected to flip.
- One live receipt before declaring done (the "registered ≠ working"
  rule): a fresh session demonstrates (a) `/recall` answering a
  trap-moment query and (b) the UserPromptSubmit hook surfacing a
  relevant lesson on a realistic prompt, recorded in decisions.md.

## D7 — What this does NOT change

- `~/.claude/memory/` global memories: untouched (non-goal).
- The Stop-hook session-stash / AMS pipeline: untouched (different
  corpus, different lifecycle).
- Sibling repos: they don't get the index in v1; `lessons.md` stays
  attune-ai-local. Cross-repo serving is the recorded later step.

## Phasing → see [tasks.md](tasks.md)
