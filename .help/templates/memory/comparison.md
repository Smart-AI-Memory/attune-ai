---
type: comparison
name: memory-comparison
feature: memory
depth: comparison
generated_at: 2026-06-10T07:07:04.805059+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Comparison: Memory backends

## Overview

The memory subsystem offers two backend tiers — a base protocol (`MemoryBackend`) and an extended protocol (`SearchableMemoryBackend`) — plus two complementary integration paths: Redis-backed short-term memory and Claude Code file-based memory (`ClaudeMemoryLoader`). Choosing the right combination depends on whether you need distributed state, semantic search, or static project context loaded at startup.

## Backend protocol comparison

| Capability | `MemoryBackend` | `SearchableMemoryBackend` |
|---|---|---|
| Basic store / retrieve / delete | ✅ `stash`, `retrieve`, `delete` | ✅ inherits all base methods |
| Key-pattern listing | ✅ `keys(pattern)` | ✅ |
| Connection health check | ✅ `is_connected()`, `get_stats()` | ✅ |
| Distributed support | runtime flag via `supports_distributed()` | runtime flag via `supports_distributed()` |
| Real-time pub/sub support | runtime flag via `supports_realtime()` | runtime flag via `supports_realtime()` |
| Semantic search | ❌ | ✅ `search(query, limit, **filters)` |
| Long-term memory promotion | ❌ | ✅ `promote(session_id)` |
| Content-addressed storage | ❌ | ✅ `remember(content, memory_id, session_id, topics)` |
| Pruning by age | ❌ | ✅ `prune(max_age_days)` |
| Recent-item retrieval | ❌ | ✅ `recent(limit, **filters)` |

`SearchableMemoryBackend` is a strict superset of `MemoryBackend`. There is no scenario where the base protocol is preferable on features alone; the base protocol exists so that lightweight backends can satisfy the contract without implementing search infrastructure.

## Storage path comparison

| Dimension | Redis short-term memory | Claude file memory (`ClaudeMemoryLoader`) |
|---|---|---|
| **Backing store** | Redis instance (local or remote) | Filesystem (`CLAUDE.md` files) |
| **Persistence** | TTL-controlled; evicted when TTL expires or Redis restarts | Persists as long as the file exists; survives process restarts |
| **Scope** | Per-agent or shared across agents via `agent_id` param | Per-project; scoped by `project_root` in `ClaudeMemoryConfig` |
| **Distributed** | Yes — multiple agents share one Redis | No — file reads are local to the process |
| **Import depth** | N/A | Configurable via `max_import_depth` (default 5 levels) |
| **File size guard** | N/A | Enforced via `max_file_size_bytes` (default 1 MB) |
| **Entry point** | `get_redis_memory(url, use_mock)` | `ClaudeMemoryLoader(config).load_all_memory(project_root)` |
| **Railway support** | `get_railway_redis()` — raises `OSError` if `REDIS_URL` is absent | Not applicable |
| **Availability check** | `is_redis_available()` — safe to call without importing Redis | No equivalent; file presence is the availability signal |
| **Typical data** | Ephemeral agent state, session keys, short-lived values | Project conventions, framework guidelines, reusable instructions |

## Feature matrix: enterprise control plane

`MemoryControlPanel` adds an operational layer on top of Redis short-term memory. It has no equivalent for file-based memory.

| Operation | API method | Notes |
|---|---|---|
| Redis lifecycle | `start_redis(verbose)`, `stop_redis()` | Only relevant when `ControlPanelConfig.auto_start_redis` is `True` |
| Health and stats | `health_check()`, `get_statistics()`, `status()` | Returns `MemoryStats` / `dict` |
| Pattern management | `list_patterns(classification, limit)`, `delete_pattern(pattern_id, user_id)` | Supports classification filtering |
| Bulk operations | `clear_short_term(agent_id)`, `export_patterns(output_path, classification)` | Export writes to a file path |
| HTTP API surface | `run_api_server(panel, host, port, api_key, ...)` | Includes rate limiting, SSL, and CORS via `RateLimiter` and `APIKeyAuth` |

There is no `MemoryControlPanel` equivalent for `ClaudeMemoryLoader`. If you need audit logging, PII scrubbing (`PIIScrubber`), secrets detection (`SecretsDetector`), or access classification (`ClassificationRules`), those are Redis-path concerns.

## Decision guide

**Use Redis short-term memory (`get_redis_memory`) when:**
- Multiple agents need to share state within or across sessions — `supports_distributed()` must return `True`.
- You need TTL-controlled eviction: stale values should disappear automatically.
- You are deploying to Railway and have a Redis add-on; use `get_railway_redis()`.
- You need the enterprise control plane: audit logging, pattern export, PII scrubbing, or the HTTP API.
- You want real-time coordination between agents (pub/sub via `supports_realtime()`).

**Use `ClaudeMemoryLoader` when:**
- You need to inject static project context — coding conventions, framework rules, project-specific instructions — into an agent at startup.
- The content lives in `CLAUDE.md` files and is edited by humans, not written programmatically.
- You want zero infrastructure: no Redis, no network, no TTLs.
- Memory must survive process restarts without any explicit persistence code.

**Use `SearchableMemoryBackend` (over `MemoryBackend`) when:**
- Your backend implementation supports semantic search and you want to expose `search`, `remember`, `promote`, and `prune` to callers.
- You are writing a backend adapter and the underlying store (e.g., a vector database) can satisfy the full contract.

**Stick with the base `MemoryBackend` when:**
- You are implementing a lightweight backend (mock, in-memory, or test fixture) that does not need search.
- You want to enforce at the type level that a component only uses simple key-value operations.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
