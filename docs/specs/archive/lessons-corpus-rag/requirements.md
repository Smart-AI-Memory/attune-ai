# Lessons Corpus via RAG — Requirements

**Status:** complete (2026-06-12) — T1–T6 done; reconciled at 2026-07-14 triage (was: approved)
**Born:** discipline-review chat, 2026-06-11 (improvement #2 of 6).

## Problem

`.claude/CLAUDE.md` is the project's engineering memory and it works —
sessions demonstrably avoid known traps because lessons load up front.
But the mechanism is front-loading ~350k characters into EVERY session:

- **Context tax.** The corpus competes with working context all
  session, every session, whether or not any lesson applies.
- **It has already broken production.** The sdk-subprocess-isolation
  spec exists because the full session context (CLAUDE.md included)
  poisoned SDK subprocess stream-json channels.
- **Consolidation has plateaued.** The consolidate-claude-md-lessons
  pass cut ~15% and hit the honest ceiling: the remaining lessons are
  genuinely distinct domain singletons. Volume will only grow.
- **Relevance competes with volume.** A lesson that matters NOW is
  one of 300+; recall depends on the model noticing it. The
  duplicate-lesson lesson ("grep before appending") exists precisely
  because the corpus outgrew casual scanning.

The retrieval machinery to fix this is already shipped and measured:
attune-rag (>99% per-claim faithfulness, golden-query benchmark
methodology, `DirectoryCorpus` + `extra_summaries`), and
just-in-time-recall's PreToolUse `additionalContext` channel (Phase 1
live-proven 2026-06-10). That spec explicitly deferred "semantic
retrieval over the full lesson corpus" as a non-goal — this spec is
that deferred layer.

## Outcome

Sessions carry a small always-loaded core of lessons; the long tail
lives in a retrievable store and surfaces only when relevant — at
session start (topic-scoped) and at instrumented decision points —
with no measured loss of trap-avoidance.

## Scope

- **Corpus:** the `.claude/CLAUDE.md` Lessons section (the dominant
  bulk). The user-profile / project-rules header stays always-loaded.
- **Retrieval surfaces:** (a) the `/recall` skill, (b) SessionStart
  topic-scoped injection, (c) just-in-time-recall map entries that
  query the store instead of carrying inline text.
- **Consumers:** interactive Claude Code sessions in this repo first;
  sibling repos later.

## Requirements

- **R1 — Phase 0 measures before anything moves.** Two numbers gate
  the design: (a) the actual per-session context cost of the Lessons
  section (chars/tokens, % of window); (b) retrieval quality on a
  golden-query set built from REAL trap moments — take ~25 incidents
  the lessons exist to prevent (e.g. "tests pass locally, fail on
  Windows CRLF"), query the store, measure the governing lesson's
  P@1/P@3. The corpus-summaries lesson applies: validate metadata
  reaches the retriever before tuning anything.
- **R2 — Tiered split, not a cliff.** A curated always-loaded core
  (target: the ~20 highest-frequency / highest-blast-radius lessons,
  e.g. worktree paths, commit hygiene, secret handling) stays in
  CLAUDE.md. Everything else moves to the store. The split criteria
  are written down and reviewable.
- **R3 — One write path.** Appending a lesson stays as cheap as
  today (edit one file). The store ingests from the lesson files —
  no second authoring format, no dual-maintenance. Near-duplicate
  detection at ingest replaces the manual pre-append grep.
- **R4 — No regression on trap avoidance.** Acceptance is behavioral:
  for the golden-query incident set, the governing lesson must be
  retrievable at the moment it matters (session-start topic match or
  decision-point trigger). A measured miss-rate worse than the
  always-loaded baseline on high-severity lessons blocks the cutover.
- **R5 — Fail-safe and reversible.** Store unavailable → sessions
  degrade to core-only and say so once. The full corpus remains in
  git; reverting the split is a file move, not a data migration.
- **R6 — Dogfood story is explicit.** The shipped result is also a
  demo: "attune-rag over our own engineering memory," measured with
  the same golden-query methodology used for `.help`.

## Non-goals (this spec)

- Migrating `~/.claude/memory/` global memories (different lifecycle,
  already small and indexed).
- Embedding-provider changes — use what attune-rag already ships
  (keyword-first; fastembed only if Phase 0 shows keyword retrieval
  under the quality gate, per the pre-committed-matrix discipline).
- Auto-curating WHICH lessons exist (consolidation stays human-led).
- Cross-repo serving (attune-help/attune-rag/author corpora) — later.

## Done when

- Phase 0 numbers recorded in `decisions.md` (context cost + golden
  P@1/P@3) with a pre-committed go/no-go threshold, BEFORE design.
- If go: CLAUDE.md carries core + pointer; the tail is retrievable;
  R4's behavioral gate passes; one release note documents the
  context-size reduction.
- If no-go: the measured reason is recorded and the spec closes —
  the corpus stays front-loaded, and we know what it buys us.
