---
feature: memory
summary: Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security
tags: [memory, storage]
source_globs:
  - src/attune/memory/**
nav:
  help: memory
  mkdocs:
    how-to: how-to/memory
    architecture: architecture/memory
    reference: reference/memory
---

## Overview

Attune's memory subsystem gives agents two tiers of storage behind one
API: **short-term** working memory (fast, TTL-expiring, optionally
Redis-backed) and **long-term** pattern memory (durable, searchable,
classified). Security runs before anything durable is written —
auto-classification, PII scrubbing, secrets detection, and at-rest
encryption for sensitive patterns.

The recommended entry point is **`UnifiedMemory`**, which composes both
tiers and the security layer behind a single object. It is
environment-aware: a `MemoryConfig` auto-detected from the environment
chooses backends (in-process for development, Redis for production) so
the same code runs in either. For custom backends, two protocols —
`MemoryBackend` and `SearchableMemoryBackend` — define the short-term
and searchable contracts.

You reach memory these ways:

- the Python API — `from attune.memory import UnifiedMemory` (the
  primary surface, documented throughout);
- the **`MemoryBackend` / `SearchableMemoryBackend` protocols** (in
  `attune.memory.backend`) — for wiring a custom store (any class
  implementing the methods works);
- **`ClaudeMemoryLoader`** — for static project context merged from
  `CLAUDE.md` files;
- **`MemoryControlPanel`** — a runtime management surface for browsing,
  exporting, and clearing stored memory.

`UnifiedMemory`'s public methods are synchronous — call them directly,
no `await`.

## Concepts

### Two tiers, one object

`UnifiedMemory(user_id=...)` exposes both tiers:

- **Short-term** — a keyed working store: `stash(key, value,
  ttl_seconds=None)` writes, `retrieve(key)` reads. Entries expire
  after `ttl_seconds` (or the config default). Backed by Redis when
  available, an in-process store otherwise.
- **Long-term** — durable, searchable **patterns**:
  `persist_pattern(content, pattern_type, ...)` stores one,
  `recall_pattern(pattern_id)` reads it back, and `search_patterns(
  query=..., limit=10)` queries by content. Patterns can be **staged**
  first (`stage_pattern(...)`) and later **promoted** to durable
  storage (`promote_pattern(staged_id)`).

### Construction is environment-aware

`UnifiedMemory` takes a required `user_id`, an optional `config`
(`MemoryConfig`, default auto-detected from the environment), and an
optional `access_tier` (`AccessTier`, default `CONTRIBUTOR`).
`MemoryConfig.from_environment()` reads `ATTUNE_`-prefixed variables
(`EMPATHY_` also accepted) — `ATTUNE_ENV` selects `development`,
`staging`, or `production`, which in turn drives Redis and storage
defaults. Construct one with explicit settings via
`UnifiedMemory(user_id="me", config=MemoryConfig(...))`.

### Security runs before durable writes

When you persist a pattern, classification and scrubbing run first.
`auto_classify=True` (the default) assigns a `Classification` —
`PUBLIC`, `INTERNAL`, or `SENSITIVE` — from the content and pattern
type; PII is scrubbed and credential-like content is flagged before
storage; `SENSITIVE` patterns are encrypted at rest. You can pass an
explicit `classification` to override the auto-assignment. Reads honor
the caller's `access_tier` unless you set `check_permissions=False` on
`recall_pattern`.

### Capabilities tell you what the backend can do

A deployment's backend may or may not support real-time updates,
distribution across processes, or durable persistence. `UnifiedMemory`
surfaces this: `get_capabilities()` returns a `dict[str, bool]`, and
`supports_realtime()`, `supports_distributed()`, and
`supports_persistence()` answer individually. `health_check()` and
`get_backend_status()` report runtime state. Check capabilities before
relying on, say, cross-process coordination.

### Custom backends implement a protocol

`MemoryBackend` is a `@runtime_checkable` `Protocol` for short-term
stores: `stash(key, value, ttl, agent_id)`, `retrieve(key, agent_id)`,
`delete(key)`, `keys(pattern)`, `is_connected()`, `get_stats()`,
`close()`, plus `supports_realtime()` / `supports_distributed()`.
`SearchableMemoryBackend` extends it with `search(query, limit)`,
`remember(content, ...)`, `promote(session_id)`, `prune(max_age_days)`,
and `recent(limit)`. Any class implementing the methods satisfies the
protocol — no base class to inherit. (Note these protocol signatures —
`stash(key, value, ttl, agent_id)` — differ from `UnifiedMemory`'s
own `stash(key, value, ttl_seconds)`.)

### Static project context

`ClaudeMemoryLoader` resolves `CLAUDE.md` files at enterprise, user,
and project levels and merges them via its `load_all_memory()` method.
Which levels load is controlled by the `MemoryConfig` **fields**
`load_enterprise_memory` / `load_user_memory` / `load_project_memory`
(not loader methods). This is the static counterpart to the read/write
tiers above.

## Quickstart

Create a memory for a user, stash some working data, and persist a
durable pattern. Every call is synchronous:

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="agent@company.com")

# Short-term working memory (expires)
memory.stash("current_task", {"id": 42, "phase": "review"}, ttl_seconds=3600)
task = memory.retrieve("current_task")

# Long-term pattern memory (durable, classified)
result = memory.persist_pattern(
    content="Use heapq.nlargest for top-N instead of sorted()[:N]",
    pattern_type="optimization",
)
if result:
    pattern = memory.recall_pattern(result["pattern_id"])

memory.close()
```

`UnifiedMemory()` with no `config` auto-detects the environment, so the
same code runs against an in-process store in development and Redis in
production.

## Tasks

### Stash and retrieve short-term working memory

**Goal:** keep transient working state that expires on its own.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
memory.stash("draft", {"step": 3}, ttl_seconds=600)  # expires in 10 min
print(memory.retrieve("draft"))                       # {"step": 3}
memory.close()
```

**Verify:** `stash` returns `True` on success; `retrieve` returns the
value or `None` if missing/expired. `ttl_seconds` is optional — omit it
to use the config default.

### Persist, search, and recall long-term patterns

**Goal:** store a durable, classified pattern and find it later by
content.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
result = memory.persist_pattern(
    content="Validate file paths with _validate_file_path before writing",
    pattern_type="security",
)
hits = memory.search_patterns(query="file path validation", limit=5)
for hit in hits:
    print(hit["pattern_id"])
memory.close()
```

**Verify:** `persist_pattern` returns a dict with a `pattern_id` (or
`None` if storage is unavailable). `search_patterns` returns a list of
dicts ranked by relevance; narrow it with `pattern_type=` or
`classification=`. Classification is automatic unless you pass
`classification=`.

### Stage a pattern, then promote it

**Goal:** hold a candidate pattern for review before committing it to
durable storage.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
staged_id = memory.stage_pattern(
    {"content": "Candidate: cache AST parses by file hash"},
    pattern_type="optimization",
)
# ... review memory.get_staged_patterns() ...
if staged_id:
    memory.promote_pattern(staged_id)
memory.close()
```

**Verify:** `stage_pattern` returns a staged id (or `None`);
`get_staged_patterns()` lists what's pending; `promote_pattern`
graduates it to durable storage (running classification/scrubbing) and
returns the stored pattern dict.

### Record an SBAR handoff

**Goal:** leave a structured handoff for the next session or agent.

**Steps:**

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="me")
memory.set_handoff(
    situation="Mid-refactor of the release agents",
    background="Split into focused submodules",
    assessment="Tests green; docs not yet updated",
    recommendation="Update docs/architecture/release.md next",
)
print(memory.generate_compact_state())
memory.close()
```

**Verify:** `set_handoff` takes the four SBAR fields plus arbitrary
`**extra_context`. `generate_compact_state()` returns a string snapshot;
`export_to_claude_md(path=None)` writes the state to a `CLAUDE.md`-style
file and returns the `Path`.

## Reference

The recommended surface is `UnifiedMemory` from `attune.memory`. The
security/loader classes (`Classification`, `PIIScrubber`,
`SecretsDetector`, `AuditLogger`, `ClaudeMemoryLoader`,
`MemoryControlPanel`) are re-exported from `attune.memory` too; the
backend **protocols** live in `attune.memory.backend` (they are not
re-exported from the package root).

### `UnifiedMemory` — `attune.memory`

| Symbol | Purpose |
|--------|---------|
| `UnifiedMemory(user_id, config=MemoryConfig.from_environment(), access_tier=AccessTier.CONTRIBUTOR)` | Construct the unified memory. `user_id` is required. |
| `stash(key, value, ttl_seconds=None) -> bool` | Write short-term working memory. |
| `retrieve(key) -> Any \| None` | Read short-term memory; `None` if missing/expired. |
| `persist_pattern(content, pattern_type, classification=None, auto_classify=True, metadata=None) -> dict \| None` | Store a durable pattern (classified + scrubbed first). |
| `recall_pattern(pattern_id, check_permissions=True, use_cache=True) -> dict \| None` | Read a durable pattern by id. |
| `search_patterns(query=None, pattern_type=None, classification=None, limit=10) -> list[dict]` | Query durable patterns by content/type/classification. |
| `stage_pattern(pattern_data, pattern_type="general", ttl_hours=24) -> str \| None` | Stage a candidate pattern; returns a staged id. |
| `promote_pattern(staged_pattern_id, classification=None, auto_classify=True) -> dict \| None` | Promote a staged pattern to durable storage. |
| `get_staged_patterns() -> list[dict]` | List pending staged patterns. |
| `get_capabilities() -> dict[str, bool]` | Backend capability flags. |
| `supports_realtime() / supports_distributed() / supports_persistence() -> bool` | Individual capability checks. |
| `health_check() -> dict` / `get_backend_status() -> dict` | Runtime state. |
| `set_handoff(situation, background, assessment, recommendation, **extra)` | Record an SBAR handoff. |
| `generate_compact_state() -> str` / `export_to_claude_md(path=None) -> Path` | Snapshot state; write it to a CLAUDE.md-style file. |
| `clear_pattern_cache() -> int` / `save() -> None` / `close() -> None` | Cache and lifecycle management. |

### `MemoryConfig` — selected fields

| Field | Default | Meaning |
|-------|---------|---------|
| `environment` | `Environment.DEVELOPMENT` | `development` / `staging` / `production`. |
| `redis_url` / `redis_host` / `redis_port` | `None` / `localhost` / `6379` | Short-term backend coordinates. |
| `redis_mock` / `redis_auto_start` / `redis_required` | `False` / — / — | In-process mock, auto-start, or require Redis. |
| `default_ttl_seconds` | — | Default short-term expiry. |
| `storage_dir` | — | Long-term pattern storage directory. |
| `encryption_enabled` | — | Encrypt `SENSITIVE` patterns at rest. |
| `load_enterprise_memory` / `load_user_memory` / `load_project_memory` | — | Which `CLAUDE.md` levels `ClaudeMemoryLoader` loads. |

Build one from the environment with `MemoryConfig.from_environment()`.

### Backend protocols — `attune.memory.backend`

| Protocol | Methods |
|----------|---------|
| `MemoryBackend` | `stash(key, value, ttl, agent_id)`, `retrieve(key, agent_id)`, `delete(key)`, `keys(pattern)`, `is_connected()`, `get_stats()`, `close()`, `supports_realtime()`, `supports_distributed()`. |
| `SearchableMemoryBackend` | Extends `MemoryBackend` with `search(query, limit)`, `remember(content, ...)`, `promote(session_id)`, `prune(max_age_days)`, `recent(limit)`. |

Both are `@runtime_checkable` — any class implementing the methods
satisfies the protocol.

### Security and loader surface — `attune.memory`

| Symbol | Role |
|--------|------|
| `Classification` | `PUBLIC` / `INTERNAL` / `SENSITIVE`. |
| `PIIScrubber` | Strips personally identifiable information before storage. |
| `SecretsDetector` | Flags credential-like content. |
| `AuditLogger` | Records writes/reads as `AuditEvent`s for compliance. |
| `ClaudeMemoryLoader` | Resolves + merges `CLAUDE.md` levels; entry point `load_all_memory()`. |
| `MemoryControlPanel` | Runtime management — browse, export, and clear stored memory. |

### Entry points

| Surface | Invocation |
|---------|------------|
| Python (recommended) | `from attune.memory import UnifiedMemory`. |
| Custom backend | Implement `MemoryBackend` / `SearchableMemoryBackend` (from `attune.memory.backend`). |
| Static context | `ClaudeMemoryLoader().load_all_memory()`. |
| Runtime management | `MemoryControlPanel`. |

## Comparison

Memory's two tiers serve different retention horizons:

| Tier | API | Lifetime | Backed by |
|------|-----|----------|-----------|
| Short-term | `stash` / `retrieve` | TTL-expiring (seconds–days) | Redis or in-process |
| Long-term | `persist_pattern` / `recall_pattern` / `search_patterns` | Durable | Persistent storage |
| Staging | `stage_pattern` / `promote_pattern` | Until promoted or expired | Short-term, then long-term |
| Static | `ClaudeMemoryLoader.load_all_memory()` | Read-only project files | `CLAUDE.md` files |

Reach for **short-term** working memory for transient state, **staging
+ promotion** when a pattern should be reviewed before it becomes
durable, and **long-term patterns** for knowledge you'll search later.
`UnifiedMemory` exposes all three; `ClaudeMemoryLoader` is the separate
static-context path.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `TypeError: __init__() missing 1 required positional argument: 'user_id'` | `UnifiedMemory()` constructed without `user_id` | Pass `user_id` — it is required | high |
| `persist_pattern` / `stage_pattern` returns `None` | Long-term storage unavailable (e.g. no writable `storage_dir`) | Check `health_check()` / `get_backend_status()`; confirm storage config | medium |
| `retrieve` returns `None` for a key you stashed | The entry expired (`ttl_seconds`) or the backend isn't persistent | Re-stash with a longer TTL; check `supports_persistence()` | medium |
| Cross-process reads don't see another process's writes | The backend isn't distributed (in-process store) | Check `supports_distributed()`; configure Redis | medium |
| `recall_pattern` returns `None` for a real id | `check_permissions=True` and the caller's `access_tier` is insufficient | Use a higher `access_tier`, or pass `check_permissions=False` for trusted callers | medium |
| A `SENSITIVE` pattern stored unencrypted | `encryption_enabled` is off in the config | Enable encryption in `MemoryConfig` | medium |

### Risk areas

- **`user_id` is required.** `UnifiedMemory` is per-user; there is no
  zero-arg constructor.
- **Protocol vs. `UnifiedMemory` signatures differ.** The protocol's
  `stash(key, value, ttl, agent_id)` is not `UnifiedMemory`'s
  `stash(key, value, ttl_seconds)` — don't conflate them.
- **Capabilities are deployment-dependent.** Real-time, distribution,
  and persistence vary by backend — check before relying on them.

### Diagnosis order

1. Confirm construction: `UnifiedMemory(user_id="...")`.
2. `health_check()` / `get_backend_status()` for backend state.
3. `get_capabilities()` to confirm realtime/distributed/persistence.
4. For a missing short-term key, check the TTL and
   `supports_persistence()`.
5. For a missing pattern, check `pattern_id`, `access_tier`, and
   `check_permissions`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What does the memory subsystem do?
  **A:** It gives agents two tiers of storage behind one API:
  short-term working memory (TTL-expiring, optionally Redis-backed)
  and long-term pattern memory (durable, searchable, classified).
  Security — auto-classification, PII scrubbing, secrets detection,
  and at-rest encryption for sensitive patterns — runs before
  anything durable is written. The recommended entry point is
  `UnifiedMemory`.
- **Q:** What's the difference between short-term and long-term memory?
  **A:** Short-term (`stash` / `retrieve`) is TTL-expiring working
  storage. Long-term (`persist_pattern` / `recall_pattern` /
  `search_patterns`) is durable, searchable, classified pattern
  storage. Patterns can be staged first (`stage_pattern`) and
  promoted later (`promote_pattern`).
- **Q:** How do I construct a UnifiedMemory?
  **A:** `UnifiedMemory(user_id="...")`. `user_id` is required;
  `config` (a `MemoryConfig`, default auto-detected from the
  environment) and `access_tier` (default `AccessTier.CONTRIBUTOR`)
  are optional. Import it with
  `from attune.memory import UnifiedMemory`.
- **Q:** Do I need Redis?
  **A:** No. `UnifiedMemory` auto-detects the environment and uses an
  in-process store when Redis isn't available; Redis adds real-time
  and cross-process support. Check `supports_distributed()` /
  `get_capabilities()` to see what the active backend supports.
- **Q:** Are the calls async?
  **A:** No — `UnifiedMemory`'s public methods are synchronous. Call
  them directly, no `await`.
- **Q:** How is sensitive data protected?
  **A:** On `persist_pattern`, content is auto-classified (`PUBLIC` /
  `INTERNAL` / `SENSITIVE`), PII is scrubbed, secrets are flagged,
  and `SENSITIVE` patterns are encrypted at rest when encryption is
  enabled. Keep `auto_classify=True` unless you set the level
  yourself.
- **Q:** What is staging for?
  **A:** `stage_pattern` holds a candidate pattern so you can review
  it (`get_staged_patterns()`) before `promote_pattern` commits it to
  durable storage (running classification and scrubbing on the way).
- **Q:** How do I write a custom backend?
  **A:** Implement the `MemoryBackend` protocol (or
  `SearchableMemoryBackend` for search) from `attune.memory.backend`
  — both are `@runtime_checkable`, so any class implementing the
  methods satisfies them. Note the protocol's
  `stash(key, value, ttl, agent_id)` differs from `UnifiedMemory`'s
  own `stash(key, value, ttl_seconds)`.

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `UnifiedMemory`, `MemoryConfig`, and the security/loader classes
  re-exported from `attune.memory`, plus the `MemoryBackend` /
  `SearchableMemoryBackend` protocols from `attune.memory.backend`.
  Submodule internals (`mixins/`, `short_term/`, `long_term_*`) may
  change.
- **Let classification run.** Keep `auto_classify=True` unless you have
  a reason to set the level yourself.
- **Check capabilities, don't assume.** Use `get_capabilities()` /
  `supports_*()` before relying on real-time or cross-process behavior.
- **Close when done.** Call `close()` (or `save()`) to flush and
  release the backend.

## Design & extension

### Design decisions

- **One object over two tiers.** `UnifiedMemory` composes short-term,
  long-term, staging, and security so callers use one API instead of
  wiring backends by hand. The tiers remain separately addressable via
  the protocols.
- **Environment-aware by default.** `MemoryConfig.from_environment()`
  picks backends from `ATTUNE_`-prefixed variables, so the same code
  runs in development (in-process) and production (Redis) without
  branching.
- **Security before durability.** Classification, PII scrubbing,
  secrets detection, and encryption run on the persist path — durable
  storage never receives unclassified or unscrubbed content.
- **Protocols, not base classes.** `MemoryBackend` /
  `SearchableMemoryBackend` are `@runtime_checkable` protocols, so a
  custom store needs only to implement the methods.

### Extension points

- **Swap the backend:** implement `MemoryBackend` (or
  `SearchableMemoryBackend`) and point the config at it.
- **Tune retention:** set `default_ttl_seconds` and per-call
  `ttl_seconds` / `ttl_hours`.
- **Control classification:** pass an explicit `classification` to
  `persist_pattern` / `promote_pattern`, or rely on `auto_classify`.
- **Manage at runtime:** use `MemoryControlPanel` to browse, export,
  and clear stored memory without code changes.
