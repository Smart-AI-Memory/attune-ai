# Claude Cross-Session Memory — Requirements

**Status:** complete (shipped — session_recall/session_stash hooks + /recall skill; live-hook activation is a deploy step)
**Approved:** 2026-06-02

## Problem

Claude's current cross-session memory is static: `~/.claude/memory/` (45 files)
loads in full every session. Gaps:

1. Context cost grows linearly — loading all memories regardless of relevance.
2. Worktree fragmentation — project memories are cwd-keyed, so the same project
   across worktrees splits into separate memory namespaces.
3. Session findings are lost — Claude learns something useful mid-session but
   can't persist it unless explicitly asked to write a memory file.

## In scope

### R1 — Automatic context injection at session start

At SessionStart, a hook queries the Redis recall index and injects the
`top-k` most relevant memories (by semantic similarity to the current
working context: cwd, open spec, last commit) into the session context.
`k` stays small enough to be noise-free (target ≤ 5 entries, ≤ 400 tokens).

**Acceptance criteria:**
- Hook runs in ≤ 1 second; failure degrades silently (no hook error banner).
- Injected entries are clearly labeled (e.g. `## Recalled memories`).
- With no Redis available, hook exits 0 (file-only fallback returns empty).
- Auto-inject does not duplicate entries already in `~/.claude/memory/`
  (curated layer is already loaded by CLAUDE.md).

### R2 — User-invoked `/recall` skill for on-demand deep pulls

A `/recall [query]` skill lets Patrick explicitly surface relevant memories
mid-session. It queries both Redis and the curated file layer, presents ranked
results with relevance rationale, and lets Patrick choose what to inject into
the conversation.

**Acceptance criteria:**
- Invocable as `/recall` (no args → infers from conversation context) or
  `/recall <query>` (explicit topic).
- Returns results from both Redis working memory and curated files.
- Shows source, type, and a one-line relevance note for each result.
- Gracefully degrades: if Redis is absent, returns curated-file results only.

### R3 — Per-session auto-stash to Redis (TTL-gated)

After each session, findings Claude considers notable (patterns, decisions,
project state, bugs encountered) are auto-stashed to Redis with a 7-day TTL.
Stashed entries feed the recall index (R1, R2) but do not modify the curated
`~/.claude/memory/` layer without explicit review.

**Acceptance criteria:**
- Findings are extracted at session end (Stop hook or explicit command).
- Each stashed entry carries: timestamp, cwd, session-id, type, content.
- PII scrubber + secrets detector run at write (reuse attune-ai gates).
- TTL default: 7 days. Configurable via `~/.attune/config.json`.
- Promoting a stashed entry to curated files requires explicit user approval
  (the existing `/remember` workflow or equivalent).

### R4 — Cross-worktree recall (content-keyed, not cwd-keyed)

The recall index keys entries on content/topic, not exact cwd. A memory
about `RedisShortTermMemory` written in a worktree session surfaces in any
other worktree or main checkout when queried.

**Acceptance criteria:**
- Recall works across cwd variants: main checkout, any worktree, sibling repos.
- No duplicate entries for identical content written from different cwds.

### R5 — Redis-optional: graceful file-only fallback

Redis is an optional dep (attune-ai pattern). The system works without it,
degrading to file-only with no auto-stash and no semantic search.

**Acceptance criteria:**
- With no Redis, R1 hook exits 0, R2 returns curated-file results only.
- No import errors, no console noise when Redis is absent.

## Out of scope

- Memory graph (nodes/edges) — separate effort.
- Persistent/always-running agent processes.
- Weakening the curated-layer review discipline.
- Enterprise/organization-level scope hierarchy (user+project is sufficient).
