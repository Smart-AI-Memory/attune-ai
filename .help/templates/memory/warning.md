---
type: warning
name: memory-warning
feature: memory
depth: warning
generated_at: 2026-06-10T07:07:04.789830+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Memory cautions

## What to watch for

The memory subsystem spans short-term Redis storage, long-term `MemDocsStorage`, Claude memory file loading, and a security layer that classifies and encrypts patterns. The risks below reflect the points where these layers interact in ways that are easy to overlook.

## Risk areas

### Secrets and PII stored without classification

`MemDocsStorage` and `SecureMemDocsIntegration` apply classification rules automatically, but only when the content passes through their security layer. If you write directly to a `MemoryBackend` via `stash()`, the `SecretsDetector` and `PIIScrubber` are bypassed entirely. Content containing values that match `HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, or `SENSITIVE_PATTERN_TYPES` will be stored in plaintext with no access controls.

**Mitigation:** Route writes that may contain sensitive content through `SecureMemDocsIntegration` rather than calling `stash()` directly on a backend.

### `get_redis_memory()` silently falls back to a mock backend

`get_redis_memory()` accepts a `use_mock` parameter. When `use_mock` is `None` (the default), the function reads an environment variable to decide. In environments where that variable is unset or Redis is unreachable, it may silently return a mock backend. Code that assumes a real Redis connection — for example, anything relying on TTL expiry or pub/sub via `CHANNEL_SESSIONS` — will appear to work but will not persist data or coordinate across agents.

**Mitigation:** Call `is_redis_available()` before `get_redis_memory()` to confirm the Redis subsystem is reachable, or check `is_connected()` on the returned backend before proceeding.

### `get_railway_redis()` raises `OSError` when `REDIS_URL` is missing

`get_railway_redis()` has no fallback. If `REDIS_URL` is not set in the environment, it raises `OSError` immediately with instructions to run `railway add --database redis`. This is intentional, but it means any startup path that calls this function without a guard will crash the process rather than degrading gracefully.

**Mitigation:** Check for `REDIS_URL` in the environment before calling `get_railway_redis()`, or wrap the call and handle `OSError` explicitly.

### `ClaudeMemoryLoader` follows imports up to `max_import_depth`

`ClaudeMemoryConfig` defaults to `max_import_depth: int = 5`. `ClaudeMemoryLoader.load_all_memory()` follows `@import` directives in CLAUDE.md files recursively to that depth. A deeply nested or circular import chain will not raise an error at depth 5 — it will silently truncate. If your project memory relies on files at depth 6 or beyond, those files will not be loaded and `get_loaded_files()` will not list them.

**Mitigation:** Keep import chains shallow. Call `get_loaded_files()` after `load_all_memory()` to verify the expected files were included.

### `max_file_size_bytes` silently skips large memory files

`ClaudeMemoryConfig` defaults to `max_file_size_bytes: int = 1000000` (1 MB). Files that exceed this limit are skipped without raising an exception. A CLAUDE.md that grows past 1 MB through accumulated lessons or imports will be excluded from the loaded context with no visible indication.

**Mitigation:** Set `validate_files: bool = True` in your `ClaudeMemoryConfig` (the default) and monitor the size of memory files in long-running projects.

### `promote()` on `SearchableMemoryBackend` moves all session data

`SearchableMemoryBackend.promote()` transfers memory from a session to long-term storage. The `session_id` parameter is optional; if omitted, the method uses a default session. Calling `promote()` without an explicit `session_id` in a multi-agent setup — where multiple agents share a Redis instance via `KEY_ACTIVE_AGENTS` — can promote the wrong session's data.

**Mitigation:** Always pass an explicit `session_id` to `promote()` when running more than one agent against the same backend.

### `clear_short_term()` on `MemoryControlPanel` is not scoped by default

`MemoryControlPanel.clear_short_term()` accepts an `agent_id` parameter that defaults to `'admin'`. Passing the wrong `agent_id`, or relying on the default in a multi-agent deployment, will clear memory belonging to a different agent rather than the intended one.

**Mitigation:** Pass the specific `agent_id` whose short-term memory you intend to clear, and confirm with `get_statistics()` before and after.

## How to avoid problems

1. **Verify backend identity before writing.** Call `is_connected()` on any `MemoryBackend` instance before writing session-critical data. For Railway deployments, confirm `REDIS_URL` is set before calling `get_railway_redis()`.

2. **Route sensitive content through the security layer.** Direct `stash()` calls bypass `SecretsDetector`, `PIIScrubber`, and `EncryptionManager`. Use `SecureMemDocsIntegration` for any content that might contain values matching the HEALTHCARE, FINANCIAL, or PROPRIETARY keyword sets.

3. **Audit loaded memory files explicitly.** After `load_all_memory()`, call `get_loaded_files()` to confirm your expected CLAUDE.md files are present. Missing files are almost always caused by `max_import_depth` or `max_file_size_bytes` limits.

4. **Scope destructive operations to a specific agent.** Pass explicit `agent_id` and `session_id` arguments to `clear_short_term()` and `promote()` to avoid operating on the wrong agent's data in shared-Redis deployments.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
