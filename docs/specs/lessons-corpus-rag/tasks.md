# Lessons Corpus via RAG — Tasks

**Status:** draft (2026-06-11) — pending design approval. Bounded
PRs; each task names its receipt.

## T1 — `attune.lessons` module

- `split_lessons()` (moved from the Phase 0 harness, which then
  imports it), atomic sub-splitting of multi-bullet lessons (D3),
  `LessonsIndex` with mtime-cached rebuild, `retrieve(query, k)`.
- Tests: splitter counts (375 top-level on the current corpus —
  assert ≥, not ==), wrap-aware title extraction, child-doc
  generation, mtime invalidation, retrieval smoke against 3 golden
  queries. Benchmark script re-run green via the shared splitter.
- One PR. No behavior change anywhere else yet.

## T2 — `/recall` extension

- The recall skill queries `LessonsIndex` alongside the AMS findings
  store; results labeled by source ("lesson" vs "session finding").
- Receipt: a trap-moment query answered in a live session.

## T3 — UserPromptSubmit hook

- `plugin/hooks/lesson_recall.py`: score floor, top-3,
  surface-once-per-(session, lesson) sentinel, `additionalContext`
  injection, `ATTUNE_LESSON_RECALL=0` off-switch, fail-safe exit 0,
  SDK-subprocess gate (`is_sdk_subprocess()` — the isolation rule).
- Tests mirror `jit_recall.py`'s suite (sentinel, no-match silence,
  crash → exit 0, injected payload shape).
- Receipt: live session shows a relevant lesson surfacing on a
  realistic prompt, and an unrelated prompt surfacing nothing.

## T4 — jit-recall `lesson_ref` integration

- `_recall_map.py` entries may reference a lesson slug; resolved
  through `LessonsIndex` at fire time. Convert one existing inline
  entry as the proof.

## T5 — The cutover (gated on T1–T3 receipts)

- Move the Lessons section (minus the D4 core) from
  `.claude/CLAUDE.md` to `.claude/lessons.md`; core selection
  reviewed by Patrick in the PR; pointer paragraph appended.
- Re-run the golden benchmark against the real file via
  `attune.lessons` — P@3 ≥ 80% holds (D6) or the cutover PR doesn't
  merge.
- Grep guard: nothing else parses CLAUDE.md's Lessons section
  (check `scripts/`, hooks, tests) before the move.
- Receipt: fresh-session context measurement before/after (the
  ~116k-token reduction, recorded in decisions.md), plus the D6
  live-receipt pair.

## T6 — Docs + release note

- CHANGELOG entry with the measured context reduction; a short
  `docs/` note on the lessons workflow (append → retrieve); the R6
  dogfood story ("attune-rag over our own engineering memory") in
  the README's RAG section if Patrick wants the marketing surface.
