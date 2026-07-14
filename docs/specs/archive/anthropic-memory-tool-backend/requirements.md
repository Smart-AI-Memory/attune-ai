# Spec: Anthropic Memory-Tool Backend

> Make attune's memory store a **drop-in backend for Anthropic's
> Memory tool** (`memory_20250818`). Anthropic's Memory tool is
> client-side — Claude issues file-style commands
> (`view`/`create`/`str_replace`/`insert`/`delete`/`rename`) against
> a `/memories` directory and *you* implement the storage. We
> implement it over attune's existing memory backends (file +
> `attune_redis.AMSMemoryBackend`), so the same durable, Redis-backed
> store that powers SessionStart recall also serves Anthropic's
> native memory interface. This turns "we do memory the way Anthropic
> suggests" into "our memory layer **is** a backend for Anthropic's
> Memory tool, persisted on Redis's Agent Memory Server."

**Status:** complete — Phase 1 shipped (`memory/memory_tool.py`, #671) + exported from `attune.memory`; Phase 2 surfacing shipped as the `attune memory-agent` CLI. Option ③ (SDK-native-workflow surfacing) re-scoped out — see design.md Phase 2.
morning review
**Owner:** Patrick + agent
**Related:**

- [`docs/redis/best-practice-alignment.md`](../../redis/best-practice-alignment.md)
  — why this is the one bridge that makes the dual-vendor claim
  demonstrable
- `claude-api` skill → Memory tool (`memory_20250818`,
  `BetaAbstractMemoryTool`) — the interface we implement
- `attune_redis.AMSMemoryBackend` / `attune.memory.file_stash` —
  the backends we map onto
- [`project_redis_strategy_leverage`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_redis_strategy_leverage.md)
  — "leverage their work" strategy this serves

---

## Problem

attune already has a durable cross-session memory store (file
backend by default, AMS/Redis when configured) and uses it for
SessionStart recall, Stop-hook stash, and `/recall`. But that store
is wired to attune's *own* internal `MemoryBackend` protocol. It is
**not** exposed through Anthropic's native **Memory tool**
interface, so:

1. We can only claim *analogy* with Anthropic's memory guidance, not
   a demonstrable integration.
2. Any agent built on the raw Claude API + Memory tool can't reuse
   attune's Redis-backed store without bespoke glue.

## Goal

Ship a `BetaAbstractMemoryTool` subclass that implements Anthropic's
six memory commands over attune's backends, so:

- A raw-API or Agent-SDK caller can pass attune's memory tool to
  `tool_runner()` and get a Redis-backed `/memories` directory.
- The same store is shared with attune's SessionStart recall (one
  memory, two interfaces).

## Requirements

- **R1 — Implement the six commands.** `view`, `create`,
  `str_replace`, `insert`, `delete`, `rename` over a path-addressed
  memory namespace, matching Anthropic's Memory tool contract.
- **R2 — Back it with attune's existing backends.** Default to the
  file backend (zero infra); use `AMSMemoryBackend` when AMS is
  configured. No new storage layer.
- **R3 — Path↔key mapping.** Memory file paths (`/memories/foo.md`)
  map to backend keys; file *content* is the stored value.
  `str_replace`/`insert` are read-modify-write on the retrieved
  text. `view` of a directory lists keys under the path prefix.
- **R4 — Security parity.** Enforce attune's path-validation rules on
  memory paths (no traversal, no absolute escapes); never persist
  provider secrets (reuse the session-redaction gate). Per-user
  namespacing when a user id is available.
- **R5 — Shared store, not a parallel one.** The Memory-tool view and
  attune's SessionStart recall read/write the *same* namespace, so a
  finding written by one surface is visible to the other (subject to
  the kv-vs-long-term distinction in design.md).
- **R6 — Graceful + tested.** Best-effort error handling (never crash
  the agent loop); mocked unit tests for all six commands + one live
  round-trip integration test (auto-skips without AMS), matching the
  existing attune_redis test discipline.

## Non-goals

- Not replacing attune's internal `MemoryBackend` protocol — this is
  an *adapter onto* it.
- Not implementing Anthropic's server-side Managed-Agents memory
  stores (different product; see design.md note).
- No semantic-search exposure through the Memory tool in v1 (the
  Memory tool is file-addressed; long-term semantic recall stays on
  `/recall`).

## Done when

- The adapter passes Anthropic's Memory tool contract for all six
  commands (mocked).
- A live round-trip writes via the Memory tool and reads back via
  attune's recall path (and vice versa) against AMS 0.14.0.
- `docs/redis/best-practice-alignment.md` can cite this as shipped.
- The README / docs can state the dual-vendor claim with a code
  pointer.
