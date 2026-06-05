---
type: warning
name: memory-warning
feature: memory
depth: warning
generated_at: 2026-06-04T23:45:26.859307+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Memory cautions

## What to watch for

The memory subsystem spans Redis-backed short-term storage, file-based CLAUDE.md loading, long-term pattern storage, and a security/classification layer. Mistakes in this area can expose secrets, corrupt cached state, or silently drop data with no error raised.

## Risk areas

### `get_redis_memory()` silently falls back to a mock

`get_redis_memory()` accepts a `use_mock` parameter that, when `None`, resolves its value from the environment. If `REDIS_URL` is unset and no explicit `use_mock=False` is passed, the function may return a mock backend instead of a real Redis connection — and your code will appear to work while writing to nowhere. Always verify the backend type in environments where persistence matters, and pass `use_mock` explicitly rather than relying on environment inference.

### `get_railway_redis()` raises `OSError` when `REDIS_URL` is missing

`get_railway_redis()` raises `OSError` if `REDIS_URL` is not set in the environment. The error message instructs you to run `railway add --database redis`, but the failure happens at call time, not at import time. If you use this function in an initialization path, an unconfigured deployment will fail at startup rather than at the first memory operation. Add an `is_redis_available()` check before calling it, or handle the `OSError` explicitly.

### `ClaudeMemoryLoader` follows `@import` chains up to `max_import_depth`

`ClaudeMemoryConfig` has a `max_import_depth` field (default `5`) and a `max_file_size_bytes` field (default `1_000_000`). `ClaudeMemoryLoader` will silently stop following imports once either limit is reached. If your CLAUDE.md hierarchy is deeper than five levels, the loader loads a partial view without raising an error. Set `max_import_depth` explicitly when your project structure requires deeper nesting, and call `get_loaded_files()` after `load_all_memory()` to confirm which files were actually read.

### `MemoryBackend.stash()` TTL defaults to `None` (no expiry)

The `stash` method on `MemoryBackend` accepts an optional `ttl` parameter. When `ttl=None`, entries are stored without an expiry. In long-running processes or multi-agent deployments, unbounded entries accumulate in Redis and are never evicted. Pass an explicit TTL for any data that does not need to survive the session, and use `get_stats()` periodically to monitor key counts.

### `SecretsDetector` and `PIIScrubber` must be called explicitly

The memory subsystem includes `SecretsDetector` and `PIIScrubber`, but neither runs automatically when you call `stash()` or `remember()`. If you store user-supplied content or environment-derived strings without first running them through these utilities, secrets and PII can end up in Redis or in exported pattern files. Call `detect_secrets()` on any externally sourced content before storing it.

### `MemoryControlPanel.clear_short_term()` defaults to the `admin` agent

`clear_short_term()` accepts an `agent_id` parameter that defaults to `'admin'`. In a multi-agent deployment, calling it without specifying an `agent_id` clears only keys belonging to the `admin` agent — which may give a false impression that short-term memory has been fully flushed. Pass the correct `agent_id` for each agent whose memory you intend to clear.

### `get_redis_config()` is marked legacy

`get_redis_config()` returns a plain `dict` built from environment variables and is documented as a legacy API. New code should use `parse_redis_url()` or construct a `RedisConfig` instance directly. Mixing both approaches in the same codebase can produce inconsistent connection parameters if environment variables are partially set.

## How to avoid problems

- **Confirm your backend before writing data.** After constructing a memory backend, call `is_connected()` to verify you have a live connection. A mock backend returns `True` from `is_connected()` in some configurations, so also check `supports_distributed()` if your workload requires cross-session coordination.

- **Audit loaded files after initialization.** Call `ClaudeMemoryLoader.get_loaded_files()` immediately after `load_all_memory()` and log the result. Truncated import chains are not reported as errors, so this is the only way to confirm the full context was loaded.

- **Set explicit TTLs for short-lived data.** Any entry stored with `ttl=None` persists until manually deleted. Prefer explicit TTLs in development and staging environments to avoid stale keys interfering with test runs.

- **Run secret detection before storing external content.** Use `detect_secrets()` on any string that originates outside your codebase before passing it to `stash()` or `remember()`.

- **Depend only on the public API.** Names prefixed with `_` — including `_CLAUDE_MD_START` and `_CLAUDE_MD_END` — are implementation details that can change without notice.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
