# Claude Cross-Session Memory — Decisions

**Status:** approved
**Ratified:** 2026-06-02

## D1 — Recall trigger

**Decision:** SessionStart hook (auto top-k) + `/recall` skill (user-invoked).

**Rationale:** For a solo developer who is always present, a skill is superior
to an autonomous MCP tool for on-demand recall: it's explicit, shows what was
surfaced and why, and puts the user in control. The hook handles "background"
context that should always be available, while `/recall` handles intentional
deeper pulls. No Claude-autonomous mid-session recall without user intent.

**Rejected alternatives:**
- On-demand MCP tool only — Claude autonomously calls it; less transparent for
  solo dev who wants to see what memory is active.
- Hook + MCP tool (original design lean) — replaced by Hook + Skill for better
  solo-dev UX.

---

## D2 — Write / promotion policy

**Decision:** Session findings auto-stash to Redis with a TTL (7 days default).
Promotion from Redis to the curated `~/.claude/memory/` layer stays
review-gated (no auto-promotion).

> **Refined by D4 (2026-06-03):** the *mechanism* for "recall over the
> ephemeral stash" was under-specified here. `RedisShortTermMemory` is
> key/value working memory, not a semantic store — see D4 for the
> three-tier resolution and the corrected API surface.

**Rationale:** Consistent with the principle that the curated layer is
human-tuned. Auto-stash captures useful findings without requiring explicit
`/remember` invocations. The TTL prevents Redis from becoming a graveyard of
stale data. Review-gated promotion keeps the curated layer's signal-to-noise
high and auditable.

**Rejected alternatives:**
- Auto-promote to curated — risks filling the curated layer with unreviewed
  content; harder to audit what Claude wrote vs what Patrick wrote.
- Manual only — loses session findings that seemed trivial at the time.

---

## D3 — Cross-memory reference format

**Decision:** `[[link]]` stays as reference (lint-checkable name resolution
only); `@import` reserved for explicit inline-composition when content must
be inlined.

**Rationale:** `[[link]]` is already enforced by `memory_lint.py` and is cheap
(no content loading). Reserving `@import` for intentional composition keeps
the distinction clear: a `[[link]]` is "this memory is related," an `@import`
is "inline this memory's content here." Most cross-references are the former.

**Rejected alternatives:**
- `@import` everywhere — higher context cost; every reference pulls full file.
- `[[link]]` only, no inline — loses composition capability for cases where
  context genuinely needs to be merged (e.g. a meta-memory that aggregates
  multiple related topics for a complex project).

---

## D4 — Recall architecture (resolves the design-vs-reality gap)

**Ratified:** 2026-06-03, after the mandatory verify-first pass against the
real memory APIs.

### What the verify pass found

The design synthesized its reuse map from scouts and cited method names that
do not exist. Verified reality:

- `PersonalMemory.capture(topic, content, kind, strict_polish=False,
  project_local=False) -> Path` — writes a **polished markdown doc** (runs the
  LLM polish pipeline; **not** a fast path). There is **no** `.store()`.
- `PersonalMemory.query(query, k=3, kind_filter=None) -> list[dict]` —
  rag-ranked **semantic** recall over the markdown corpus (global +
  project-local merged); returns `path`/`summary`/`excerpt`/`score`. This is
  the semantic-recall primitive.
- `RedisShortTermMemory.stash(key, data, credentials: AgentCredentials, ttl)
  -> bool` + `.retrieve(key, credentials) -> Any` — key/value working memory
  with TTL; **requires `AgentCredentials`**; **key-based, not semantically
  searchable**. There is **no** `.store()`.

**The gap:** D2's "auto-stash to Redis ephemeral **+ recall semantically**"
cannot be served as written — Redis short-term memory is key/value, not a
semantic store. Neither naive option is right alone:

- *(a) recall only over durable files* → ephemeral findings are invisible to
  recall until promoted; defeats cross-session continuity of raw findings.
- *(b) build a semantic index over the Redis stash* → unscoped new work
  (embeddings/index over Redis values).

### Decision — three-tier: cheap-write / semantic-read / gated-promote

1. **Write (Stop hook, T1.2):** stash **raw** findings fast, **no LLM polish**
   — `RedisShortTermMemory.stash()` if available (TTL), else JSONL fallback
   `~/.attune/session_stash/<date>.jsonl`. Polishing at write would make the
   Stop hook slow and costly; the polish is deferred to promotion.
2. **Recall (SessionStart T1.1 + `/recall` T2.1):** `recall_entries(query,
   top_k, cwd)` **merges two sources**, each labeled by origin:
   - **durable/curated:** `PersonalMemory.query()` — semantic, rag-ranked.
   - **recent stash:** a cheap **keyword + tag + recency + same-cwd filter**
     over the raw stash. The stash is one user × 7-day TTL — small enough that
     semantic search is unnecessary; recency + keyword suffices.
3. **Promote (`/recall` T2.1 + T2.2, user-gated):** `PersonalMemory.capture()`
   — the **only** LLM-polish path, moving a stash entry into the durable,
   semantically-searchable tier. The LLM cost lands here, user-gated
   (consistent with D2's review-gated promotion).

This **rejects (b)** (no new semantic index), **refines (a)** (ephemeral
findings *are* recalled — via the cheap filter, not semantic search), and maps
cleanly onto every existing primitive. `recall_entries`'s "semantic" property
applies to the durable tier; the ephemeral tier is recency/keyword.

### Consequences for tasks.md

- Every `PersonalMemory.store()` → `.capture()` (promote) or `.query()`
  (recall). Every `RedisShortTermMemory.store()` → `.stash()` / `.retrieve()`.
- `recall_entries` (T1.3) is a **merge** of two backends, not a single call.
- T1.2 / T1.3 must obtain an `AgentCredentials` for the Redis calls (construct
  a session-scoped credential — implementation detail for build time).

### Cross-spec note (B → C)

`PersonalMemory.query()` runs attune-rag's `KeywordRetriever` with
`MIN_ALIAS_OVERLAP = 2` over `~/.claude/memory`, which is **not** alias-tuned.
C's recall quality is therefore a direct victim of the alias-overlap regression
addressed by the **alias-overlap-remediation** spec (attune-rag PR #154). C
should use the documented subclass override (`MIN_ALIAS_OVERLAP = 1`) for the
personal-memory corpus, **or** measure recall quality and decide. This is a
concrete instance of that spec's consumer-impact item.
