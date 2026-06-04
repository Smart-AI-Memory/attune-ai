# Tasks — Wire `expand_async` into attune-ai workflows

## Phase 1 — Identify async consumers

- [ ] **1.1** Grep attune-ai's workflows for existing `async def`
      / `await` patterns:
      `grep -rln "async def\|await " src/attune/workflows/`
- [ ] **1.2** Cross-reference with sites that call attune-rag:
      `grep -rln "from attune_rag\|attune_rag\." src/attune/`
- [ ] **1.3** Produce a list of candidate call-sites where
      attune-rag is called from an async context (these are
      the Phase 2 targets)
- [ ] **1.4** For each candidate, record current behavior:
      blocking? `asyncio.run()`? `loop.run_until_complete()`?
      `asyncio.to_thread()`?

## Phase 2 — Migrate call-sites (one at a time)

For each candidate from 1.3, in order of estimated value:

- [ ] **2.x.1** Switch the call from `expand(...)` to
      `await expand_async(...)`
- [ ] **2.x.2** Remove any `asyncio.run()` / `loop.*` wrapping
      that's no longer needed
- [ ] **2.x.3** Add a small test asserting concurrent invocations
      complete in roughly half the time of sequential ones
- [ ] **2.x.4** Push, watch CI, verify no regression
- [ ] **2.x.5** Move to next call-site

## Phase 3 — Defer sync-only consumers

For workflows where the entire call chain is sync (not just the
RAG site), DO NOT force-migrate. Instead:

- [ ] **3.1** Identify them and record why each is sync-only
- [ ] **3.2** File separate specs if any of those workflows
      could benefit from full async (e.g., parallel
      orchestration). Don't bundle here.

## Phase 4 — Close

- [ ] **4.1** Migration log in decisions.md: what migrated, what
      deferred, why
- [ ] **4.2** Mark spec **Resolved**

## Out of scope

- Adding new async APIs to attune-rag — just consuming
  `expand_async`
- Migrating any non-RAG sync-to-async paths
- Performance optimization of attune-rag's internals
- Coordination with attune-help / attune-author async paths
  (separate concern)
