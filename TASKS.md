# Tasks

## Active

- [ ] **windows-exit139-segfault** — hypothesis confirmed
  (2026-07-06), fix plan drafted in
  `docs/specs/windows-exit139-segfault/` but not landed.
  Next step: execute the drafted fix plan. (TODO added
  2026-07-16 — deferred from 9:32 session.)
- [ ] **usage-signals** — requirements approved 2026-06-11
  (owner: patrick + agent); no design/tasks yet. Next step:
  design pass via `/spec`. (TODO added 2026-07-16 —
  deferred from 9:32 session.)

## Waiting On

- [ ] **trap-battery v2 + fable task 9** — gated post-freeze
  (2026-07-28+); design approved 2026-07-13. Do not start
  before the freeze lifts.

## Someday

- [ ] **Phase 2 optimizations** — Profile hot paths, generator
  migration, data structure optimization
  (see `.claude/rules/attune/advanced-optimization-plan.md`)
- [ ] **Advanced strategies** - Implement ToolEnhanced,
  PromptCached strategies in `orchestration/_strategies/`
- [ ] **commands dead-code gate pass** — run the
  removing-dead-code gate over `src/attune/commands/`
  (loader/parser/registry/models + command `.md` corpus); ruled
  pickable by context-compaction-retirement D2 (chair,
  2026-08-18); verify consumers against the tree at pick-up time
  (see `docs/specs/context-compaction-retirement/decisions.md`)

## Done

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
