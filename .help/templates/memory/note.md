---
type: note
name: memory-note
feature: memory
depth: note
generated_at: 2026-07-14T15:58:54.095241+00:00
source_hash: cba94c001e0b9e2f41279e9caa28b69cdc1ff0b0c62ec76baa038dc0e48cb5b6
status: generated
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

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
