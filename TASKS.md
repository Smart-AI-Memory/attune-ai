# Tasks

> Reconciled 2026-08-28 against the tree. Every item below was
> verified — spec status lines, merged PRs, and the actual
> modules on disk — not carried forward on its own text. Five
> of the seven items this file carried were already done or
> pointed at a moved file; see Done.

## Active

- [ ] **release-16-manifest passenger 4** — the harness-lite
  extension system, and the only remaining passenger of the
  16.0.0 major (1/2/3/5 shipped in #2331/#2333/#2334).
  `attune.extensions` does not exist on disk; 16.0.0 and 16.1.0
  both shipped without it. Mechanism ruled twice (D1 2026-08-26
  via full round table; D2 2026-08-27 confirmed on the
  author-experience criterion — do NOT re-pitch the config-key
  downsize). Next step: **chair ruling on the PROPOSED D3
  phasing** in `docs/specs/release-16-manifest/decisions.md`
  (three vertical slices; Phase A = memory backends, whole
  author loop, target 16.2.0).

- [ ] **usage-signals US-7 closure entry** — was listed here as
  "no design/tasks yet, next step: design pass", which is stale:
  `phase2-design.md` has existed since 2026-06-15, and
  US-1/2/4/5/6/7 shipped with US-3 closed 2026-08-09 (D17).
  The real remainder is US-7's refreshed done-when closure
  entry — a spec-record task, not a design pass.

## Waiting On

- [ ] **fit_source budget ratification** — ruling C
  (context-compaction-retirement D3, 2026-08-19) deferred the
  hardcoded 1250/1250/1000/750 budgets until measurement data
  exists. Status 2026-08-28: the writer is live
  (`src/attune/context/allocator.py:30`) but
  `~/.attune/telemetry/context_fit.jsonl` **does not exist** —
  no data has accumulated at all, so the clock has not started.
  Worth one check that the path is actually exercised before
  waiting further on it.

## Someday

- [ ] **commands dead-code gate pass** — run the
  removing-dead-code gate over `src/attune/commands/`
  (5 `.py` modules + the command `.md` corpus); ruled pickable
  by context-compaction-retirement D2 (chair, 2026-08-18);
  verify consumers against the tree at pick-up time
  (see `docs/specs/context-compaction-retirement/decisions.md`).

- [ ] **Phase 2 optimizations** — profile hot paths, generator
  migration, data structure optimization. NOTE: the plan this
  pointed at was archived, not deleted — it now lives at
  `docs/archive/planning/advanced-optimization-plan.md`, not
  `.claude/rules/attune/`. Re-validate the plan against the
  current tree before picking it up; an archived plan is a
  hypothesis, not a scope.

## Done

- [x] ~~**Advanced strategies** — ToolEnhanced, PromptCached~~
  ALREADY IMPLEMENTED, found during the 2026-08-28 reconcile:
  `ToolEnhancedStrategy` and `PromptCachedSequentialStrategy` in
  `src/attune/orchestration/_strategies/advanced_strategies.py`
  (lines 25 and 141). Carried as "Someday" while shipped.
- [x] ~~**windows-exit139-segfault**~~ — carried here as "fix
  plan drafted but not landed"; in fact #1282 landed 2026-07-06,
  the spec has read `shipped` since 2026-07-20, and it was closed
  out with a loopback regression guard in #1520.
- [x] ~~**trap-battery v2**~~ (2026-07-14) — carried as "gated
  post-freeze, do not start"; the full 120-session battery had
  already run. `docs/specs/trap-battery/requirements.md:20`
  states it verbatim: "trap-battery v2" is DONE.
- [x] ~~**fable task 9**~~ (2026-08-09) — same stale gate; the
  spec's tasks.md reads "complete — task 9 closed, all 9 tasks
  done".
- [x] ~~Book container — `docs/process/BOOK_OUTLINE.md` (outline
  hypothesis + load-bearing seed index + container rules)~~
  (2026-07-16)
- [x] ~~LLM API integration~~ (Mar 2026)
- [x] ~~Phase 1 list copy optimizations~~ (Jan 2026)
- [x] ~~Documentation reorganization~~ (Jan 2026)
- [x] ~~Security path validation across 77+ files~~ (Jan 2026)
- [x] ~~CLI & slash command reorganization~~ (Jan 2026)
- [x] ~~Set up TASKS.md, memory/ directory, clean orphaned
  READMEs~~ (Feb 2026)
