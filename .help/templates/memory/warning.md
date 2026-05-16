---
type: warning
name: memory-warning
feature: memory
depth: warning
generated_at: 2026-05-16T06:14:13.794835+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Memory cautions

## What to watch for

The memory subsystem handles storage, lookup, and security across Redis-backed short-term memory, file-based Claude memory (CLAUDE.md), and long-term pattern storage. Mistakes here can silently drop data, expose secrets, or produce different behavior between local development and production.

## Risk areas

### Redis availability check swallows import errors silently

`is_redis_available()` returns `False` for both "Redis is not installed" and "Redis is installed but unreachable." If your code branches on this return value and Redis is actually misconfigured, you will silently fall back to a mock or no-op backend with no error logged. Always follow a `False` result by checking `check_redis_connection()` to distinguish missing dependencies from connection failures.

### `get_redis_config()` is a legacy API with environment coupling

`get_redis_config()` reads connection parameters directly from environment variables and returns a plain dict. It does not validate the values it reads. If `REDIS_URL` is malformed or missing, downstream callers like `get_redis_memory()` will fail at connection time rather than at configuration time — often with a misleading error. Prefer constructing a `RedisConfig` object explicitly, or validate the URL with `parse_redis_url()` before passing it on.

### `parse_redis_url()` does not raise on invalid input

`parse_redis_url()` returns a dict of connection parameters parsed from a URL string. It does not raise an exception if the URL is structurally invalid — it may return partial or empty values. Code that calls this function and then passes results directly to a Redis client can fail with an obscure connection error rather than a clear parse error. Check the returned dict for required keys (`host`, `port`) before using it.

### `get_railway_redis()` raises `OSError` when `REDIS_URL` is absent

Unlike the other config helpers, `get_railway_redis()` raises `OSError` if `REDIS_URL` is not set in the environment. If you call this function outside a Railway deployment, you will get an `OSError` with instructions to run `railway add --database redis`. Wrap calls to this function in an environment check or a `try/except OSError` block when using it in code that may run locally.

### `ClaudeMemoryConfig.max_import_depth` caps recursive CLAUDE.md loading

`ClaudeMemoryLoader` follows `@import` directives in CLAUDE.md files up to `max_import_depth` (default: `5`). Import chains deeper than this limit are silently truncated — no warning is raised and `load_all_memory()` returns whatever it loaded before hitting the limit. If your project uses nested imports and memory content appears incomplete, lower `max_import_depth` incrementally and call `get_loaded_files()` to confirm which files were actually loaded.

### `max_file_size_bytes` silently skips large memory files

`ClaudeMemoryConfig` sets a default `max_file_size_bytes` of 1,000,000 bytes (1 MB). Files exceeding this limit are skipped without raising an error. If a CLAUDE.md file is not being loaded and `validate_files` is `True`, check whether the file size exceeds this threshold before investigating other causes.

### Security classification keywords drive access control

The `classify_pattern()` function uses hardcoded keyword lists (`HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, `PROPRIETARY_KEYWORDS`) to assign classification levels that gate access via `check_access()`. Patterns containing words like `patient`, `credit card`, or `confidential` will be classified automatically. If a pattern is unexpectedly restricted, inspect its content against these keyword lists rather than assuming a bug in the access control logic.

## How to avoid problems

- **Distinguish unavailability from misconfiguration.** When `is_redis_available()` returns `False`, call `check_redis_connection()` to get a status dict that separates import failures from connection failures.

- **Validate Redis URLs before use.** Call `parse_redis_url()` and confirm the returned dict contains `host` and `port` before passing parameters to a Redis client.

- **Audit loaded memory files explicitly.** After calling `load_all_memory()`, call `get_loaded_files()` to verify the full set of files was loaded. Gaps indicate truncated import chains or files exceeding `max_file_size_bytes`.

- **Guard `get_railway_redis()` with an environment check.** Check for `REDIS_URL` in `os.environ` before calling this function in code that runs outside Railway, or catch `OSError` and surface a clear message.

- **Treat `_`-prefixed helpers as unstable.** Private functions in this module can change without notice. Depend only on the public API surface documented in `MemoryBackend` and `SearchableMemoryBackend`.

- **Run `pytest -k "memory"` before merging changes.** Environment variables and module-level cached values can cause memory behavior to differ between local runs and CI. If a test passes locally but fails in CI, check for implicit state from `get_redis_config()` or cached `ClaudeMemoryLoader` instances — call `clear_cache()` between tests.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
