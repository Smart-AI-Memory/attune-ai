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

> **Backend refined by D5 (2026-06-03):** the three tiers below are
> **backend-agnostic** — they run against the existing
> `SearchableMemoryBackend` protocol. The default backend is file-based
> (markdown + attune-rag keyword search); Redis Agent Memory Server is an
> optional upgrade that already implements the protocol with true vector
> search. See D5. Where tier 1 below names `RedisShortTermMemory.stash()`,
> read it as "the active backend's write path."

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

---

## D5 — Backend selection: protocol-agnostic, file default, Redis AMS optional upgrade

**Ratified:** 2026-06-03, after researching Redis's agent-memory stack
against the existing ecosystem code (Patrick's prompt: "research what Redis
has vs what we want; demote if we don't need it, add if we do").

### What the research found

attune-ai **already defines** `SearchableMemoryBackend(MemoryBackend,
Protocol)` ([`src/attune/memory/backend.py:142`](../../../src/attune/memory/backend.py))
— a `search(query, limit, **filters)` + `promote(session_id)` extension
"implemented by backends that support vector similarity search (e.g., Redis
Agent Memory Server)."

`attune_redis.AMSMemoryBackend` **already implements it**, wrapping the
**Redis Agent Memory Server** (`agent-memory-client>=0.14.0`):

- `stash()` → AMS working memory (session key/value)
- `search()` → AMS long-term memory, **vector / full-text / hybrid** semantic
  search with topic/entity/namespace/time filters
- `promote()` → AMS working → long-term promotion

Redis AMS is a **superset** of the recall need: vector+hybrid search,
automatic topic/entity extraction, background auto-promotion, and a built-in
memory lifecycle (creation/promotion/access/aging/forgetting/compaction). Its
cost is **infrastructure**: a running Agent Memory Server (HTTP service) +
Redis + the optional `agent-memory-client` dep. (`agent-memory-client` is not
installed in the default venv.)

### Decision

**Keep Redis — as the optional upgrade, not the baseline. Do not demote; do
not require.**

- **Recall is backend-agnostic.** `recall_entries()` resolves a
  `SearchableMemoryBackend` and calls `.search()` / `.promote()`. It never
  hard-codes Redis or files.
- **Default backend = file-based, zero-config.** A new file
  `SearchableMemoryBackend` impl: markdown corpus (`~/.attune/session_stash/`
  + curated `~/.claude/memory`) searched by attune-rag's `KeywordRetriever`.
  Works offline, no server, no extra dep. Query is keyword+alias+stemming
  (attune-rag's model — embeddings were ruled out for the spine corpus).
- **Optional upgrade = `AMSMemoryBackend`.** When `attune-redis` is installed
  AND an AMS server is reachable, recall transparently gains vector/hybrid
  search, auto-extraction, and native promotion — zero extra spec work
  (already built + protocol-conformant).
- Backend resolution: prefer a configured/available `SearchableMemoryBackend`
  (AMS); else fall back to the file backend. Mirrors attune-ai's existing
  `attune.memory_backends` entry-point + file-fallback pattern.

### Tier mapping (AMS vs the curated layer — do not conflate)

AMS's automatic working→long-term promotion is **not** the same as D2's
review-gated promotion to curated `~/.claude/memory`. Map three tiers:

- AMS **working memory** ≈ raw session stash (ephemeral).
- AMS **long-term memory** ≈ an auto-extracted, vector-**searchable** middle
  tier — surfaced by recall, but **not** human-curated.
- **`~/.claude/memory` curated files** ≈ the human-reviewed durable tier;
  promotion *into* it stays review-gated (D2 holds).

So with the AMS backend, recall searches AMS long-term + curated files; AMS's
background auto-promotion populates its own long-term tier and does **not**
bypass the D2 gate into curated files.

### Consequences

- The spec targets the **protocol**, not a backend. T1.3's
  `session_stash.py` ships the **file `SearchableMemoryBackend`** as the
  default impl; the AMS path is selected when present.
- No new public-surface or scope beyond the file backend — AMS is reuse.
- Supersedes the previous-turn "demote Redis to accelerator / drop it" lean:
  AMS is a real, already-built upgrade and stays as the optional high tier.

---

## D6 — This release builds on Redis AMS (file/keyword tier cut)

**Ratified:** 2026-06-03. Patrick: "if we can get it by implementing the
Redis solution that's fine for this release — no point working extra hard for
a mediocre result when we can leverage Redis." Confirmed feasible + simpler.

### Decision

For this release, **`AMSMemoryBackend` (Redis Agent Memory Server) is the sole
implemented recall backend.** The file/keyword `SearchableMemoryBackend`
(markdown + attune-rag) described in D5 is **deferred, not built** — it was
both more work and the weaker result.

The protocol seam from D5 is retained at **zero cost**: `recall_entries()` and
`session_stash.py` target the `SearchableMemoryBackend` protocol, so a file
fallback is a future drop-in, not a refactor. AMS is simply the only
implementation wired this release.

### Why this is less work AND better

1. **AMS already implements `stash` / `search` / `promote`** — we wire hooks
   to a built backend instead of authoring a retriever.
2. **Sidesteps the B-regression entirely.** AMS uses its own vector/hybrid
   search, not attune-rag's `KeywordRetriever`, so `MIN_ALIAS_OVERLAP` never
   touches the recall path. The D4 cross-spec caveat does not apply to the AMS
   path.
3. **Curated `~/.claude/memory` files are already auto-loaded every session**
   (global CLAUDE.md). Recall's distinct job is the *ephemeral session stash*
   — exactly AMS working + long-term. No need to re-query curated files via
   attune-rag; that whole tier is cut.

### Setup cost (documented for the hooks' README)

- Run the server: `uv run agent-memory api --task-backend=asyncio` (single
  process) or `docker compose up api redis`.
- Redis: already running (cloud + local:6379).
- Embedding provider (mandatory for vector search): **Ollama** (local, free,
  private — preferred for *personal* memory so findings never leave the
  machine) **or** OpenAI (`OPENAI_API_KEY`, zero extra process). Spec default:
  Ollama; override via AMS env.
- Dep: `pip install attune-ai[redis]` (pulls `agent-memory-client`).
- Env: `AMS_BASE_URL` (default `http://localhost:8000`), `AMS_NAMESPACE`,
  `REDIS_URL`.

### Graceful degradation

AMS unreachable → recall + stash are **silent no-ops** (hooks exit 0, no
banner), satisfying T1.1/T1.2 acceptance criteria. The feature requires a
running AMS to function; without it, sessions behave as they do today.

### Tier mapping under D6

- **Session stash (raw, ephemeral):** AMS working memory — `stash()`.
- **Searchable recall tier:** AMS long-term — `search()`, populated by AMS's
  background auto-extraction/promotion from working memory.
- **Curated durable tier:** `~/.claude/memory` files — unchanged; already
  auto-loaded each session; promotion *into* it stays the existing
  review-gated `/remember` flow (D2 holds, independent of AMS).

### Consequences for tasks.md

- **Cut from this release:** the file `SearchableMemoryBackend` impl, the
  attune-rag keyword wiring, the `MIN_ALIAS_OVERLAP=1` override, the
  keyword/recency stash filter (D4 tier-2 mechanics). All become the future
  file-fallback drop-in.
- **T1.3 `session_stash.py`:** wraps `AMSMemoryBackend` behind the
  `SearchableMemoryBackend` protocol; provides `recall_entries()` →
  `backend.search()` and the raw stash write → `backend.stash()`.
- **T1.1 / T1.2 hooks:** call the protocol; silent no-op when AMS is down.
- **T2.1 `/recall`:** presents `backend.search()` results; promotion to
  curated files stays the `/remember` path (D2).
- **Verify-first at build time:** confirm `agent-memory-client` installs and
  an AMS server responds at `AMS_BASE_URL` before wiring (per the
  introspect-before-coding lesson).

## D7 — Searchable-tier population: direct long-term write at stash time

> **Status:** **Ratified with Patrick 2026-06-03**, from the D6
> "verify-first at build time" pass. Option (a) chosen. Builds on
> attune-ai PR #588 (AMS backend bug fixes, merged). Implementation
> (backend write method + `session_stash` wiring + round-trip test)
> follows in a separate PR.

### What the verify-first pass found

Standing up a real local AMS (Ollama `nomic-embed-text` @ 768-dim +
Redis Stack RediSearch) to verify D6's wiring showed that **D6's
stated populate mechanism does not hold as written.** D6's "Tier
mapping under D6" says the searchable tier is "AMS long-term —
`search()`, populated by AMS's background auto-extraction/promotion
from working memory." Empirically:

1. `stash()` → `set_working_memory_data` writes the working-memory
   **data dict** (a key-value blob). AMS auto-extraction operates on
   conversation **messages**, not the data dict, so it never promotes
   the blob.
2. Auto-extraction also requires a **generation model** (default
   `gpt-5`), which contradicts the local-first / extraction-off stance
   this release wants. Pointing generation at local `llama3.1` adds
   latency on every write and is still message-based.
3. Round-trip measured: `stash` → `search` = **0 hits**, even after an
   explicit `promote()` (returns `True` but moves working *memories*,
   not the data dict).
4. **The search path itself works:** a direct
   `create_long_term_memory([record])` → `search_long_term_memory`
   returns the hit (Ollama embeddings + RediSearch verified). So the
   gap is purely the *write* path — not embeddings, index, or search.

(Two AMS backend bugs surfaced in the same pass — client construction
against `agent-memory-client` 0.14.0, and an event-loop lifecycle bug
in `_run_sync` — are fixed in PR #588, which D7 builds on.)

### The decision

How should a stashed finding reach the searchable tier?

- **(a) Direct long-term write at stash time. — Recommended.**
  `stash_entry` writes via a new `AMSMemoryBackend` method wrapping
  `create_long_term_memory([ClientMemoryRecord(...)])`. The only option
  empirically verified end-to-end; fully local (Ollama embeds on
  write); recall is immediate; no generation model; no promote step.
  Keeps the existing data-dict `stash()`/`retrieve()` for its
  key-value use. Refines D6: the searchable tier is populated by a
  **direct cheap long-term write at stash time** (embedding is the
  only cost, handled locally), not by background auto-extraction.
  D4's "cheap-write" intent holds — one create call, no LLM polish;
  curation still lives in the `/remember` promotion path (D2).
- **(b) Working memories + explicit `promote()` on session end.**
  `add_memories_to_working_memory` then `promote()` (verified
  generation-free). Two-step; defers searchability to session end.
- **(c) Re-enable auto-extraction on a local generation model.**
  Contradicts extraction-off + local-first, adds per-write latency,
  and is unverified for data-dict writes. Not recommended.

### Consequences if (a) is ratified

- attune-redis: add a long-term-write method to `AMSMemoryBackend`
  (it currently has none — only the data-dict `stash`).
- T1.3 `session_stash.py`: `stash_entry` routes the searchable write
  through that method; `recall_entries` stays `backend.search`.
- D6's "populated by AMS's background auto-extraction" bullet is
  superseded by "populated by a direct long-term write at stash time."
- Extraction stays **off**; no generation model required.

## D8 — File-fallback default; AMS becomes the optional upgrade (revisits D6)

> **Ratified with Patrick 2026-06-03**, during release-readiness
> planning. Partially **reverses D6's "cut the file/keyword tier"** —
> see rationale below.

### What release-readiness review found

Verified against the installed package:

- The `file` entry point → `FileSessionMemory`, which has **no
  `search()`** and a constructor requiring `user_id` (so
  `resolve_backend`'s no-arg `ep.load()()` can't even instantiate it).
- Only `AMSMemoryBackend` is searchable. So **without a full local
  AMS standup (Ollama + Redis Stack + agent-memory-server), recall is
  a silent no-op** — there is no graceful fallback.
- D6 had cut the file/keyword tier "to build on AMS this release,"
  which left the feature hard-requiring heavy local infra. For a
  `pip install attune-ai` dev tool, that means the *majority* of users
  would get nothing from the feature.

### Decision

**The default backend is a searchable file backend; AMS is an optional
upgrade for better recall at scale.** This restores D4's design (the
ephemeral stash tier is recalled by a cheap **keyword + recency + cwd**
filter — *not* semantic; the stash is one user × short retention, small
enough that keyword/recency suffices). Cross-session memory then works
**out-of-box for every install** with zero infra; users who want
higher-quality recall over a large corpus opt into AMS.

This supersedes D6's tier mapping: D6 said "searchable tier = AMS
long-term, file/keyword tier cut." D8 reinstates the file tier as the
default and demotes AMS to optional upgrade. D7's `remember()`-based
write path is unchanged and applies to both backends.

### Consequences / tasks

- **New `FileStashBackend`** (purpose-built, no-arg constructable):
  implements the `SearchableMemoryBackend` protocol over a local JSONL
  stash (`~/.attune/session_stash/`). `remember()` appends a finding;
  `search()` = keyword + recency + cwd filter; `stash`/`retrieve`
  key/value; age-based TTL prune. Registered as the `file` entry
  point (replaces the non-searchable `FileSessionMemory` mapping in
  the `attune.memory_backends` group — `FileSessionMemory` stays the
  general session-state facade, used directly, not via this group).
- **`resolve_backend` preference**: prefer a *connected* upgrade
  backend (AMS) over the always-available file fallback. Backends mark
  themselves with an `is_fallback` class attribute; resolve picks the
  first connected non-fallback, else a connected fallback, else None.
  (Held for implementation with Patrick — changes shared resolution.)
- **No-AMS UX**: feature works out-of-box; AMS-not-running just means
  the file fallback is used (no error, no setup required).
- Documentation frames AMS as "optional: better recall at scale,"
  with the standup steps in an advanced section, not a prerequisite.
