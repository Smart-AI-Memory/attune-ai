---
type: error
name: memory-error
feature: memory
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 7d6a88f7e825fe56e3b06e3bce6dd904fe6a75cd1c13a3a134e4b44138df245e
status: generated
---

# Memory errors

## Common error signatures

Failures in the memory subsystem fall into three categories: Redis connectivity errors, filesystem errors when loading `CLAUDE.md` memory files, and security/permission violations when accessing classified patterns.

| Exception | Likely source | Typical cause |
|---|---|---|
| `OSError: REDIS_URL not found...` | `get_railway_redis()` | `REDIS_URL` environment variable is missing from the Railway project |
| `OSError` | `create_default_project_memory()` | Target directory is not writable or `project_root` path does not exist |
| `MemoryPermissionError` | Pattern access checks | Caller's access tier does not meet the pattern's `Classification` level |
| `SecurityError` | `SecureMemDocsIntegration` | PII or secrets detected in content being stored |
| `ValueError` | `parse_redis_url()` | Malformed Redis URL passed to connection setup |
| `ConnectionError` | `MemoryBackend.is_connected()` | Redis process is not running or the configured host/port is unreachable |

## Where errors originate

Errors can arise from any of the following entry points. The function that raises is usually not the one the caller invoked — trace the chained exception (`__cause__`) to find the original raise site.

- **`get_railway_redis()`** — raises `OSError` when `REDIS_URL` is absent. The error message includes the exact Railway CLI command needed to add Redis.
- **`get_redis_memory(url, use_mock)`** — wraps environment-based Redis setup; failures here usually mean the URL is malformed or the environment variable is unset.
- **`parse_redis_url(url)`** — raises `ValueError` on a malformed URL before a connection is attempted.
- **`create_default_project_memory(project_root, framework)`** — raises `OSError` if `.claude/CLAUDE.md` cannot be written.
- **`ClaudeMemoryLoader.load_all_memory(project_root)`** — raises if `max_import_depth` is exceeded or a file exceeds `max_file_size_bytes` (default 1 000 000 bytes).
- **`MemoryControlPanel.start_redis()`** / **`stop_redis()`** — failures surface as `RedisStatus` error states or raise if the subprocess cannot be managed.
- **`MemoryBackend.stash()` / `retrieve()` / `delete()`** — raise when the backend is not connected; call `is_connected()` first to distinguish a connection failure from a logic error.

## How to diagnose

1. **Read the full exception chain.** When exceptions are re-raised with `from e`, Python prints both the original cause and the wrapper. The original cause names the exact operation that failed — do not stop at the outermost message.

2. **Check whether Redis is reachable.** Call `is_redis_available()` to test whether the Redis subsystem can be imported, then call `check_redis_connection()` to verify the live connection. A `False` or error result from either narrows the problem to infrastructure rather than application logic.

3. **Inspect `ClaudeMemoryConfig` fields when memory files fail to load.** Verify that `project_root` resolves to the correct directory, that `max_import_depth` (default 5) is not too low for your import graph, and that no file exceeds `max_file_size_bytes`. Set `validate_files = True` (the default) to surface malformed files early.

4. **Check access tier for `MemoryPermissionError`.** Pattern access is gated by `Classification` rules. Confirm the agent's access tier against the pattern's classification level. Healthcare, financial, and proprietary patterns are governed by `HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, and `PROPRIETARY_KEYWORDS` classification rules respectively.

5. **Confirm the environment variable for Railway deployments.** `get_railway_redis()` requires `REDIS_URL`. If it is absent, the error message instructs you to run `railway add --database redis`. For external access, use `REDIS_PUBLIC_URL` instead.

6. **Use `MemoryControlPanel.health_check()`** to get a structured report of Redis status, storage availability, and audit log accessibility in one call before diving into individual subsystems.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
