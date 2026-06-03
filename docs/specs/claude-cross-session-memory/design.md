# Claude Cross-Session Memory — Design Draft

> **Status: DRAFT for `/spec` intake — NOT an approved spec.** No `tasks.md`
> here is executable until this goes through `/spec` and decisions are
> ratified. Synthesizes three read-only scouts run 2026-06-02 (attune-ai
> memory subsystem, the `attune` umbrella specs, and the legacy
> empathy-framework `claude_memory`).

## Problem & honest framing

The goal is to give Claude **richer cross-session memory** — but precisely:

- Cross-session memory means *the next session's Claude can retrieve what a
  prior session wrote*. It is continuity of **knowledge**, not a running agent
  that persists between sessions. Design for knowledge-continuity; designing
  for a persistent process would be wrong.
- A **static** form already exists: `~/.claude/memory/` + `MEMORY.md` load
  every session (just hardened with a format spec + lint hook). That is how
  Claude already "remembers" preferences across sessions.
- The gap Redis fills is **selective semantic recall**: surface the relevant
  few memories for *this* task instead of loading all ~45 every session
  (already a growing context cost), and recall project knowledge that the
  cwd-keyed file store fragments across worktrees.

## Current state (grounded in the scouts)

**`~/.claude/memory/` — curated, authored (exists, hardened 2026-06-02)**
- 45 markdown files + `MEMORY.md` index, loaded every session.
- Spec R1–R4 enforced by `~/.claude/hooks/memory_lint.py` (PostToolUse):
  `name`≡filename-stem, fixed frontmatter, atomic index pointer, resolving
  `[[links]]`. Routing rule: cross-project → global, else → project.

**attune-ai — recall infrastructure (mostly exists)**
- `src/attune/memory/personal.py` `PersonalMemory`: filesystem
  `~/.attune/memory/<topic>/<kind>.md` (kinds: decision/pattern/
  troubleshooting/reference) + `summaries_by_path.json` index; semantic
  search via optional `attune_rag`.
- `src/attune/memory/short_term/facade.py` `RedisShortTermMemory`: Redis
  working memory w/ TTL, file fallback (`FileSessionMemory`).
- `src/attune/memory/long_term.py` + `attune_redis/memory.py` `AMSMemoryBackend`:
  persistent + semantic long-term (agent-memory-client).
- `src/attune/memory/unified.py` `UnifiedMemory`: mixin-composed entry point.
- Validation today: id/slug/classification regex + PII scrubber + secrets
  detector at the storage boundary. **No markdown-format/link/dedup linting.**

**Legacy empathy-framework `claude_memory` — reusable design ideas**
- `attune_llm/claude_memory.py`: 3-tier **scope hierarchy**
  (enterprise→user→project, project wins), `@path/to/file.md` **imports**
  (inline-include) with circular-detection (stack), depth limit (5), and
  resilient missing-import handling.
- `examples/claude_memory/`: security tiers (PUBLIC/INTERNAL/SENSITIVE),
  auto-classification, audit log shape — runtime policy, not file format.
- Memory graph (`src/attune/memory/graph.py`): nodes/edges knowledge graph —
  **orthogonal**, out of scope here.

## Proposed architecture — two layers that compose

**Layer 1 — Curated / authored (small, always-relevant, human-tuned)**
- The hardened `~/.claude/memory/` file format is the source of truth for
  durable preferences/process.
- Adopt from legacy `claude_memory`: the **scope hierarchy** (formalize the
  global-vs-project routing into enterprise/user/project precedence) and
  **import/link resolution** (reconcile `@import` vs `[[link]]` — see
  decisions).

**Layer 2 — Recall (large, accreted, retrieved by relevance)**
- Reuse attune-ai's `UnifiedMemory` / `PersonalMemory`+rag / Redis backends.
- Index the curated layer **and** per-session accretions into Redis; retrieve
  by semantic relevance into a session instead of loading everything.

**How they compose:** curated files stay the authoritative, reviewable record;
Redis is a derived, rebuildable recall index over them plus session findings.
Losing Redis never loses authored memory.

## Reuse map (≈80% exists — integration, not greenfield)

| Need | Source | Action |
|---|---|---|
| Durable format + lint | `~/.claude/memory` + `memory_lint.py` | reuse as-is |
| Scope hierarchy / routing | legacy `claude_memory.py` | port concept |
| Import/link resolution | legacy `@import` + our `[[link]]` | reconcile, port |
| Semantic recall | attune-ai `PersonalMemory`+rag, AMS | reuse |
| Working/session memory | attune-ai `RedisShortTermMemory` | reuse |
| Secrets/PII safety | attune-ai scrubber/detector | reuse at write |
| The binding into a Claude Code session | — | **build (thin)** |

## Open decisions (resolve in `/spec` — not pre-decided)

1. **Recall trigger** — how relevant memories enter a session:
   (a) SessionStart hook queries Redis and injects; (b) an MCP `memory_recall`
   tool Claude calls on demand; (c) extend the existing auto-memory load.
   *Lean:* (b)+(a) — auto-inject a small top-k at start, plus on-demand tool.
2. **Write policy** — what gets stashed per session and whether durable
   promotion needs Patrick's review (vs auto-promote).
   *Lean:* session findings auto-stash to Redis (ephemeral/TTL); promotion to
   the curated file layer stays **review-gated** (consistent with the curated
   layer being human-tuned).
3. **Format reconciliation** — legacy `@import` *inlines* content; our
   `[[link]]` is a *reference*. Pick one model for cross-memory references.
   *Lean:* keep `[[link]]` as reference (cheap, lint-checkable); reserve
   inline-include for an explicit `@import` only where composition is needed.

## Non-goals
- Not a persistent/always-running agent.
- Memory graph (nodes/edges) — orthogonal, separate effort.
- No weakening of the curated-layer review discipline.

## Risks / constraints
- Redis is an **optional** dependency (attune-ai pattern) — recall must degrade
  to file-only gracefully.
- Reuse the existing PII/secrets gates before anything is written to Redis.
- Worktree cwd-fragmentation of project memory is a motivating case — semantic
  recall keyed on content (not exact cwd) helps; confirm in design.
- Context budget: auto-injected top-k must stay small.

## Next step
Run `/spec` to take this from draft → approved (requirements + ratified
decisions + tasks) before any implementation. This is the release-strengthening
candidate for attune-ai; the release stays held until its scope is decided.
