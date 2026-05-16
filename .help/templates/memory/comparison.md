---
type: comparison
name: memory-comparison
feature: memory
depth: comparison
generated_at: 2026-05-16T06:14:13.808440+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Comparison: Memory backends and storage strategies

## Context

The memory subsystem provides short-term storage, semantic lookup, and security controls for Attune AI agents. Three distinct storage strategies are available: Redis-backed short-term memory (`RedisShortTermMemory`), file-based session memory (`FileSessionMemory`), and Claude Code memory files (`ClaudeMemoryLoader`). Each targets a different combination of persistence, distribution, and search capability.

## Feature comparison

| Capability | Redis (`RedisShortTermMemory`) | File session (`FileSessionMemory`) | Claude memory (`ClaudeMemoryLoader`) |
|---|---|---|---|
| **Primary purpose** | Fast short-term storage for live agents | Durable per-session storage without a running server | Load static project and user context from `CLAUDE.md` files |
| **Persistence across restarts** | No — data lives until TTL expires or `clear_short_term()` is called | Yes — written to `storage_dir` on disk | Yes — reads from committed files |
| **Distributed / multi-agent** | Yes — `supports_distributed()` returns `True`; sessions coordinated via `CrossSessionCoordinator` | No | No |
| **Semantic search** | Yes — `SearchableMemoryBackend.search()` with filters and `promote()` | No | No |
| **Real-time pub/sub** | Yes — `supports_realtime()` returns `True`; uses `CHANNEL_SESSIONS` | No | No |
| **TTL-based expiry** | Yes — per-key TTL via `stash(key, value, ttl=…)` | No built-in TTL | N/A — read-only |
| **External dependency** | Redis server required; check with `is_redis_available()` | None | None |
| **Security / PII controls** | `PIIScrubber`, `SecretsDetector`, `EncryptionManager`, `AuditLogger` | Inherits audit dir via `ControlPanelConfig` | `validate_files`, `max_file_size_bytes`, `max_import_depth` |
| **Railway / cloud setup** | `get_railway_redis()` — raises `OSError` if `REDIS_URL` is absent | Not cloud-specific | Not cloud-specific |
| **Read-only?** | No | No | Yes — `load_all_memory()` only |
| **Deprecated?** | No | No | Redis config module (`config.py`) is deprecated; use `get_redis_memory()` or `get_railway_redis()` |

## Tradeoffs in detail

### Redis short-term memory

Redis is the right backend when multiple agents share state in the same session or across sessions. `CrossSessionCoordinator` uses `KEY_ACTIVE_AGENTS` and a service lock (`KEY_SERVICE_LOCK`) to prevent conflicts. `stash()` accepts a per-key TTL, so entries expire automatically without manual cleanup. The cost is an external dependency: if Redis is unavailable, `is_redis_available()` returns `False` and you must fall back to a mock or file backend.

### File session memory

`FileSessionMemory` writes to a local `storage_dir` and requires no running server, making it suitable for single-agent workflows, CI environments, or offline development. It does not implement `supports_realtime()` or `supports_distributed()`, and it has no TTL mechanism — callers are responsible for pruning stale entries.

### Claude memory files

`ClaudeMemoryLoader` reads `CLAUDE.md` files at up to `max_import_depth` levels (default 5) and merges them into a single string via `load_all_memory()`. It is read-only: there is no `stash()` or `delete()` equivalent. Use it to inject stable project conventions, enterprise policies, or user preferences into an agent's context, not to store runtime state.

## Use Redis when…

- You run more than one agent concurrently and need shared, consistent state.
- You need key expiry without manual cleanup (`ttl` parameter in `stash()`).
- You need semantic search over stored patterns (`SearchableMemoryBackend.search()`).
- You are deploying to Railway or another cloud platform — use `get_railway_redis()` and ensure `REDIS_URL` is set.

## Use file session memory when…

- You are running a single agent in a CI job or offline environment where Redis is unavailable.
- You need persistence across process restarts but have no infrastructure budget for a Redis instance.
- You do not need semantic search or cross-agent coordination.

## Use Claude memory files when…

- You want to load static project conventions (`CLAUDE.md`) or enterprise-level guidelines (`load_enterprise=True`) into an agent at startup.
- Your memory content changes infrequently — it is committed to the repository and versioned there.
- You need to impose file-size and depth limits on what an agent can read (`max_file_size_bytes`, `max_import_depth`, `validate_files`).

## What to avoid

- Do not call `get_redis_config()` in new code — the Redis config module is marked deprecated. Use `get_redis_memory()` or `get_railway_redis()` instead.
- Do not patch the internal `MemoryBackend` protocol methods directly. If the public API (`stash`, `retrieve`, `delete`, `keys`) does not meet your needs, propose an extension via `SearchableMemoryBackend` or file an issue.
- Do not wire up `RedisShortTermMemory` for a single throwaway script. If you only need to pass data between two functions in the same process, a plain dict is faster and has no external dependency.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
