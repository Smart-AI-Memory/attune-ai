---
name: memory
source: content/features/memory.md
tags:
- memory
- storage
type: faq
---

# Memory FAQ

## What does the memory subsystem do?

It gives agents two tiers of storage behind one API:
short-term working memory (TTL-expiring, optionally Redis-backed)
and long-term pattern memory (durable, searchable, classified).
Security — auto-classification, PII scrubbing, secrets detection,
and at-rest encryption for sensitive patterns — runs before
anything durable is written. The recommended entry point is
`UnifiedMemory`.

## What's the difference between short-term and long-term memory?

Short-term (`stash` / `retrieve`) is TTL-expiring working
storage. Long-term (`persist_pattern` / `recall_pattern` /
`search_patterns`) is durable, searchable, classified pattern
storage. Patterns can be staged first (`stage_pattern`) and
promoted later (`promote_pattern`).

## How do I construct a UnifiedMemory?

`UnifiedMemory(user_id="...")`. `user_id` is required;
`config` (a `MemoryConfig`, default auto-detected from the
environment) and `access_tier` (default `AccessTier.CONTRIBUTOR`)
are optional. Import it with
`from attune.memory import UnifiedMemory`.

## Do I need Redis?

No. `UnifiedMemory` auto-detects the environment and uses an
in-process store when Redis isn't available; Redis adds real-time
and cross-process support. Check `supports_distributed()` /
`get_capabilities()` to see what the active backend supports.

## Are the calls async?

No — `UnifiedMemory`'s public methods are synchronous. Call
them directly, no `await`.

## How is sensitive data protected?

On `persist_pattern`, content is auto-classified (`PUBLIC` /
`INTERNAL` / `SENSITIVE`), PII is scrubbed, secrets are flagged,
and `SENSITIVE` patterns are encrypted at rest when encryption is
enabled. Keep `auto_classify=True` unless you set the level
yourself.

## What is staging for?

`stage_pattern` holds a candidate pattern so you can review
it (`get_staged_patterns()`) before `promote_pattern` commits it to
durable storage (running classification and scrubbing on the way).

## How do I write a custom backend?

Implement the `MemoryBackend` protocol (or
`SearchableMemoryBackend` for search) from `attune.memory.backend`
— both are `@runtime_checkable`, so any class implementing the
methods satisfies them. Note the protocol's
`stash(key, value, ttl, agent_id)` differs from `UnifiedMemory`'s
own `stash(key, value, ttl_seconds)`.
