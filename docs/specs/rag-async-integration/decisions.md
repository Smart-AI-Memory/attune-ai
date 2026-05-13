# Decisions — Wire attune-rag's `expand_async` into attune-ai workflows

**Status:** Draft (2026-05-11) — gated on briefing-followup batch
**Owner:** Patrick

---

## Problem

attune-rag PR #8 added `expand_async` to `attune_rag.expander` —
an async-aware variant of the synchronous `expand` function. It's
been merged and is part of attune-rag 0.1.10+.

In attune-ai, every consumer of attune-rag uses the **synchronous**
path (`expand`, `pipeline.run`, etc.). The async variant has no
consumer, so the API exists but its value isn't being captured.

Concrete cost: any attune-ai workflow that's already on an asyncio
event loop has to block-on-sync to call attune-rag, which:

- Holds an event-loop slot while attune-rag's I/O completes
- Loses concurrency on parallel RAG queries within a single
  workflow run
- Blocks the workflow's other async tasks (telemetry, MCP
  pubsub, etc.)

## Decision

Wire `expand_async` into attune-ai workflows that already run
async, in three phases.

## What's in scope

- **Phase 1**: identify which attune-ai workflows are already
  async (the agent SDK adapter is async-friendly;
  `rag_code_gen` workflow already uses async; some `mcp` handlers
  too)
- **Phase 2**: switch those call-sites to `expand_async` —
  one call-site at a time, with a CI check between to confirm
  no regression
- **Phase 3**: where conversion is non-trivial (sync-only
  workflows that would need full async migration), file a
  separate spec rather than force the issue

## What's NOT in scope

- Migrating sync-only workflows to async just to use
  `expand_async`. The cost of async migration exceeds the
  benefit in those cases.
- Adding `expand_async` to non-RAG paths (e.g., async pubsub,
  async streaming). Those are separate concerns.
- Changing attune-rag's API surface. Just consuming the
  existing one.

## Alternatives considered

1. **Leave as-is** — sync path works. The cost is real but
   not blocking. Acceptable indefinitely.
2. **Migrate all attune-ai workflows to async** — too
   aggressive; mixing async and sync within the orchestration
   layer creates `asyncio.run()` reentrancy bugs.
3. **Add a third intermediate API in attune-rag** (e.g., a
   thread-pool-backed wrapper) — duplicates concerns; the
   sync/async pair is the right boundary.

## Acceptance criteria

- At least one async attune-ai consumer calls `expand_async`
- Benchmark shows reduced wall-clock for the chosen workflow
  when running in parallel (e.g., a 4-query RAG run completes
  in ~T/4 wall-clock instead of ~T)
- No new bugs introduced; existing sync path unchanged for
  consumers that don't migrate
- Spec closed with a "what we migrated, what we deferred"
  log

## Execution gate

This spec is **not urgent.** It's an optimization. Don't start
execution until:

1. No in-flight CI debt (Probe C resolved ✅, Windows xdist
   queued)
2. attune-rag stable on its current release
3. attune-ai has bandwidth (not mid-major-release)

---

(per-phase decisions appended as work happens)
