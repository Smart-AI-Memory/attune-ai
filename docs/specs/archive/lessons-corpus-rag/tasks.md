# Lessons Corpus via RAG — Tasks
**Status:** complete (2026-06-12) — T1–T6 done; D6 fresh-session
receipt captured post-cutover (decisions.md).
Bounded PRs; each task names its receipt.

## T1 — `attune.lessons` module — DONE 2026-06-11

- `split_lessons()` (moved from the Phase 0 harness, which then
  imports it), atomic sub-splitting of multi-bullet lessons (D3),
  `LessonsIndex` with mtime-cached rebuild, `retrieve(query, k)`.
- Tests: splitter counts (375 top-level on the current corpus —
  assert ≥, not ==), wrap-aware title extraction, child-doc
  generation, mtime invalidation, retrieval smoke against 3 golden
  queries. Benchmark script re-run green via the shared splitter.
- One PR. No behavior change anywhere else yet.
- **Receipt:** benchmark on the frozen golden set via the real
  `LessonsIndex`: corpus 514 docs (380 lessons + 134 children);
  **P@1 84%, P@3 96%, high-severity 7/7** — clears the D6 gate.
  Two design findings recorded along the way: (a) naive child docs
  REGRESSED P@3 to 72% by displacing their parents in the top-3, so
  children carry `metadata["parent_path"]` and the benchmark credits
  child hits to their lesson; (b) `LessonsIndex.retrieve()` dedups
  the candidate pool by lesson (one mega-lesson's children can't
  occupy multiple top-k slots) — this also flipped the
  three-children-of-the-wrong-parent crowd-out. Remaining miss:
  `subscription-sdk-fail` (vocabulary collision with the
  diagnosing-sdk-failures family — the known structural-ambiguity
  class). Tests: 23, module branch coverage 100%.

## T2 — `/recall` extension — DONE 2026-06-11

- The recall skill queries `LessonsIndex` alongside the AMS findings
  store; results labeled by source ("lesson" vs "session finding").
- **Receipt:** live trap-moment query `"tag a release after a squash
  merge"` through `LessonsIndex().retrieve(k=3)` returned the exact
  child sub-lesson first — *"Tag mechanics … — Don't tag before a
  squash-merge"* (score 16.0), then the post-squash-local-main and
  branch-recreation lessons. The skill degrades silently to
  findings-only when `attune.lessons`/attune-rag is unavailable
  (older installs). `.agents/` mirror regenerated via
  `sync_agents_skills.py`.

## T3 — UserPromptSubmit hook — DONE 2026-06-11

- `plugin/hooks/lesson_recall.py`: score floor, top-3,
  surface-once-per-(session, lesson) sentinel, `additionalContext`
  injection, `ATTUNE_LESSON_RECALL=0` off-switch, fail-safe exit 0,
  SDK-subprocess gate (`is_sdk_subprocess()` — the isolation rule).
- Tests mirror `jit_recall.py`'s suite (sentinel, no-match silence,
  crash → exit 0, injected payload shape).
- **Receipt (process-level, real corpus):** payload prompt *"I need
  to tag the release now that the squash merge landed on main"* →
  injected the Tag-mechanics lesson as `additionalContext`; an
  unrelated prompt (dashboard color tweak) emitted nothing; both
  exited 0. Extra noise gates beyond the design: min prompt length
  (20 chars — short acks never query) and slash-command skip
  (`/recall` IS the manual surface). Floor tunable via
  `ATTUNE_LESSON_RECALL_FLOOR` (default 8.0) for soak calibration.
  Children sentinel on their PARENT lesson id, so one mega-lesson
  isn't re-surfaced via a different child. 17 tests.
- **In-CC-session receipt — CAPTURED 2026-06-12** (first 8.4.0
  session post-restart): see decisions.md D6. Short version: hooks
  were initially dark because the parked main checkout predated
  `attune.lessons`; after unparking, `jit_recall` fired organically
  on an AskUserQuestion call, the lesson_recall trap prompt injected
  Tag-mechanics via the real plugin-cache hook, and `/recall`
  returned labeled `[lesson]` hits with the backend named
  (AMSMemoryBackend, fallback: false).

## T4 — jit-recall `lesson_ref` integration — DONE 2026-06-12

- `_recall_map.py` entries may reference a lesson slug; resolved
  through `LessonsIndex` at fire time. Convert one existing inline
  entry as the proof.
- Shipped: optional `lesson_ref` field (documented in the map's
  authoring rules); `jit_recall._resolve_lesson()` resolves it via
  `LessonsIndex().get()` lazily at fire time — whitespace-normalized
  excerpt capped at 600 chars, appended as a "Full lesson — …" line
  below the inline one-liner. Best-effort: import failure (older
  install / stale main checkout) or a dangling slug falls back to
  the one-liner alone. Proof entry: `release-verify-merge-sha` →
  the Tag-mechanics lesson.
- **Receipt:** live fire with the `gh release create` payload
  appended the real Tag-mechanics lesson body from the corpus
  (resolve cost ~0.36 s, well inside the 3 s hook timeout). Tests
  22 (5 new): resolved-excerpt append, excerpt bound, ImportError
  fallback, unknown-slug fallback, and a drift guard asserting
  every `lesson_ref` in the map resolves against the REAL corpus
  (slugs derive from titles — a title edit dangles the ref).

## T5 — The cutover — DONE 2026-06-12 (overnight run)

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
- **Receipt (recorded in decisions.md "T5 cutover"):** CLAUDE.md
  438,783 → 41,370 chars (91%, ~99k tokens/session freed);
  benchmark vs the REAL lessons.md held P@1 84% / P@3 96% /
  high-severity 7/7; grep guard repointed 6 consumers before the
  move; core = 22 verbatim mirrored blocks (20 ratified items),
  drift-guarded by tests/unit/lessons/test_core_mirror.py.
  Remaining for D6: the fresh-session live pair on the
  post-cutover file (next session).
- **D6 fresh-session receipt — DONE 2026-06-12** (first
  post-cutover session): lesson_recall hook answered from
  lessons.md (correct top hit), SessionStart recall surfaced 5
  AMS findings, `/recall` path live on `AMSMemoryBackend`. Full
  record in decisions.md "D6 fresh-session receipt".

## T6 — Docs + release note — DONE 2026-06-12

- CHANGELOG entry with the measured context reduction; a short
  `docs/` note on the lessons workflow (append → retrieve); the R6
  dogfood story ("attune-rag over our own engineering memory") in
  the README's RAG section if Patrick wants the marketing surface.
- **Receipt:** CHANGELOG `[Unreleased]` entry (91% cut + benchmark
  numbers); `docs/how-to/lessons-workflow.md` added and wired into
  the mkdocs nav (Memory System group); README item shipped early
  via #781 (the cross-session memory loop section IS the
  marketing surface — R6 dogfood story covered there).
