---
type: concept
name: memory-concept
feature: memory
depth: concept
generated_at: 2026-06-10T07:07:04.767860+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Memory

Attune's memory system gives agents a structured way to store, retrieve, search, and secure information across sessions — from ephemeral key-value entries held in Redis to project-scoped knowledge loaded from `CLAUDE.md` files.

## Two storage tiers

The system separates memory into two distinct tiers that serve different lifespans and access patterns.

**Short-term memory** is governed by the `MemoryBackend` protocol. Any backend that implements this protocol exposes five core operations: `stash`, `retrieve`, `delete`, `keys`, and `close`, plus diagnostic methods (`is_connected`, `get_stats`). The `stash` method accepts an optional `ttl` and an optional `agent_id`, so entries can be scoped to a specific agent and expire automatically. Redis is the default short-term backend; `is_redis_available()` lets you check whether the Redis subsystem is reachable before attempting a connection.

**Long-term, searchable memory** extends the base protocol through `SearchableMemoryBackend`. This layer adds semantic operations — `search`, `remember`, `recent`, `promote`, and `prune` — that let agents query by meaning rather than exact key. `promote` moves entries from a session into durable storage; `prune` removes entries older than a configurable `max_age_days`.

## CLAUDE.md memory files

A separate mechanism handles project-scoped knowledge: `CLAUDE.md` files that live in the repository and are loaded at startup. `ClaudeMemoryLoader` reads these files according to a `ClaudeMemoryConfig`, which controls which levels are loaded (`load_enterprise`, `load_user`, `load_project`), where to look for them (`enterprise_memory_path`, `project_root`), and how deep to follow `@import` chains (`max_import_depth`, default `5`). Each file that is loaded becomes a `MemoryFile` dataclass carrying its `level`, `path`, `content`, `imports`, and `load_order`.

`load_all_memory` returns the combined content as a single string ready for injection into a model context. `get_loaded_files` lists the paths that contributed to that string, which is useful for debugging import chains. You can create a starter file for a new project with `create_default_project_memory(project_root, framework)`.

## Security and classification

Content stored in long-term memory is classified before it is persisted. The `Classification` system recognises healthcare (`HEALTHCARE_KEYWORDS`), financial (`FINANCIAL_KEYWORDS`), and proprietary (`PROPRIETARY_KEYWORDS`) content, and maps pattern types to sensitivity tiers via `SENSITIVE_PATTERN_TYPES` and `INTERNAL_PATTERN_TYPES`. `PIIScrubber` and `SecretsDetector` run as guards to prevent personally identifiable information and secrets from reaching storage. Access control is enforced through `check_access` and surfaces as `MemoryPermissionError` or `SecurityError` when a caller lacks the required tier.

## Enterprise control panel

`MemoryControlPanel` (configured via `ControlPanelConfig`) exposes operational controls for the short-term store: `start_redis`, `stop_redis`, `clear_short_term`, `list_patterns`, `delete_pattern`, `export_patterns`, and `health_check`. `get_statistics` returns a `MemoryStats` snapshot. These operations are also available over HTTP through `MemoryAPIHandler`, which applies `RateLimiter` (per-IP, sliding window) and `APIKeyAuth` before forwarding requests to the panel. Use `run_api_server` to start the HTTP interface.

## How the pieces fit together

```
Agent
  │
  ├─► MemoryBackend (stash / retrieve)          ← short-term, keyed, TTL-aware
  │       └─► RedisShortTermMemory              ← default implementation
  │
  ├─► SearchableMemoryBackend (search / remember / promote)
  │       └─► long-term semantic store          ← promoted from sessions
  │
  ├─► ClaudeMemoryLoader (load_all_memory)      ← project knowledge at startup
  │       └─► MemoryFile[]                      ← one per CLAUDE.md in the tree
  │
  └─► MemoryControlPanel                        ← operational management
          └─► MemoryAPIHandler (HTTP)            ← remote access with auth + rate limiting
```

Short-term entries flow up to long-term storage through `promote`. Long-term entries are kept fresh by `prune` and surfaced by `search` and `recent`. Project-level knowledge from `CLAUDE.md` files is read-only at runtime and injected directly into model context by `load_all_memory`.
