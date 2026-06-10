---
type: faq
name: memory-faq
feature: memory
depth: faq
generated_at: 2026-06-10T07:07:04.794691+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Memory FAQ

## What does the memory feature do?

It provides storage, lookup, and security for agent memory. The module covers short-term backends (via `MemoryBackend` and `SearchableMemoryBackend`), Claude Code memory file loading (`ClaudeMemoryLoader`), and an enterprise control panel (`MemoryControlPanel`) for managing patterns, Redis, and audit logs.

## When do I need to use the memory feature?

Use it when your agent needs to store or retrieve state across steps, load project-level `CLAUDE.md` memory files, or manage long-term patterns with classification and security controls. If you only need simple key-value caching with no agent context, a plain dict or file may be sufficient.

## How do I check whether Redis is available before using it?

Call `is_redis_available()`. It checks the Redis subsystem without importing it, so it's safe to call at startup or in a conditional import path.

## How do I get a Redis-backed memory instance?

Call `get_redis_memory(url=..., use_mock=...)`. It reads environment variables for configuration, so you can omit both arguments in most deployments. On Railway, use `get_railway_redis()` instead — it raises `OSError` with remediation instructions if `REDIS_URL` is not set.

## What is the difference between `MemoryBackend` and `SearchableMemoryBackend`?

`MemoryBackend` is the base protocol: it covers `stash`, `retrieve`, `delete`, `keys`, `is_connected`, `get_stats`, `close`, `supports_realtime`, and `supports_distributed`. `SearchableMemoryBackend` extends it with semantic search (`search`), long-term memory methods (`remember`, `promote`, `prune`), and `recent`. Use `SearchableMemoryBackend` when your backend needs semantic search or cross-session promotion.

## How do I load CLAUDE.md memory files into a project?

Instantiate `ClaudeMemoryLoader` with a `ClaudeMemoryConfig` and call `load_all_memory(project_root=...)`. The config controls which levels are loaded (`load_enterprise`, `load_user`, `load_project`), the search depth (`max_import_depth`, default `5`), and file-size limits (`max_file_size_bytes`, default `1000000`).

If you need a default memory file for a new project, call `create_default_project_memory(project_root, framework='empathy')` — it creates `.claude/CLAUDE.md` for you.

## How do I check the health of the memory control panel?

Call `MemoryControlPanel.health_check()`. For a formatted overview of status and statistics, use `print_status(panel)` and `print_stats(panel)`.

## How do I clear short-term memory for an agent?

Call `MemoryControlPanel.clear_short_term(agent_id=...)`. The default `agent_id` is `'admin'`.

## How do I debug a memory problem?

Start with `pytest -k "memory" -v` to confirm the tests pass. If they pass but your code still fails:

1. Call `is_redis_available()` to rule out a missing Redis connection.
2. Call `check_redis_connection()` for a detailed status dict.
3. Call `MemoryControlPanel.health_check()` for control-panel-level diagnostics.
4. Add `logger.debug` at the suspected failure point and re-run with logging enabled.

For symptom-based issues, see the troubleshooting page for this feature.

## Where are the source files?

All memory source files are under `src/attune/memory/`.

**Tags:** `memory`, `storage`
