---
type: task
name: memory-task
feature: memory
depth: task
generated_at: 2026-06-10T07:07:04.773986+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Work with memory

Use the memory subsystem when you need to configure, query, or secure agent memory — including short-term Redis-backed storage, Claude memory file loading, and the enterprise control panel.

## Prerequisites

- Read access to the project source under `src/attune/memory/`
- A running Redis instance, or the ability to use a mock backend (see `get_redis_memory(use_mock=True)`)
- `pytest` installed for verification

## Steps

1. **Identify the entry point for your use case.**

   Choose the function or class that owns the behavior you need:

   | Goal | Entry point | Location |
   |---|---|---|
   | Check Redis availability before connecting | `is_redis_available()` | `src/attune/memory/__init__.py` |
   | Create a project-level `CLAUDE.md` memory file | `create_default_project_memory(project_root, framework)` | `src/attune/memory/claude_memory.py` |
   | Parse a Redis URL into connection parameters | `parse_redis_url(url)` | `src/attune/memory/config.py` |
   | Load Redis config from environment variables | `get_redis_config()` | `src/attune/memory/config.py` |
   | Instantiate a `RedisShortTermMemory` backend | `get_redis_memory(url, use_mock)` | `src/attune/memory/config.py` |
   | Verify the Redis connection status | `check_redis_connection()` | `src/attune/memory/config.py` |
   | Connect to a Railway-hosted Redis instance | `get_railway_redis()` | `src/attune/memory/config.py` |
   | Start the Memory API server | `run_api_server(panel, host, port, api_key, ...)` | `src/attune/memory/control_panel_api.py` |
   | Manage enterprise memory patterns and statistics | `MemoryControlPanel` | `src/attune/memory/control_panel_api.py` |
   | Load and cache `CLAUDE.md` files | `ClaudeMemoryLoader` | `src/attune/memory/claude_memory.py` |

2. **Configure the backend for your environment.**

   - For short-term Redis-backed memory, call `get_redis_memory()`. Pass a `url` argument to override the default environment variable lookup, or set `use_mock=True` to run without a Redis server.
   - For Claude memory file loading, instantiate `ClaudeMemoryLoader` with a `ClaudeMemoryConfig`. Set `enabled=True` and configure `load_enterprise`, `load_user`, and `load_project` to control which memory scopes are imported. Use `max_import_depth` and `max_file_size_bytes` to cap resource usage.
   - For the enterprise control panel, instantiate `MemoryControlPanel` with a `ControlPanelConfig`. Set `redis_host`, `redis_port`, and `storage_dir` to match your deployment. Set `auto_start_redis=True` if you want the panel to manage the Redis process.

3. **Call the appropriate protocol methods on the backend.**

   If you are working with a `MemoryBackend` directly, use these methods:

   - `stash(key, value, ttl, agent_id)` — write a value
   - `retrieve(key, agent_id)` — read a value
   - `delete(key)` — remove a value
   - `keys(pattern)` — list keys matching a glob pattern
   - `is_connected()` — confirm the backend is reachable
   - `get_stats()` — retrieve usage statistics

   If your backend implements `SearchableMemoryBackend`, you also have:

   - `remember(content, memory_id, session_id, topics)` — store a memory with metadata
   - `search(query, limit, **filters)` — run a semantic search
   - `recent(limit, **filters)` — fetch the most recent memories
   - `promote(session_id)` — promote session memories to long-term storage
   - `prune(max_age_days)` — remove memories older than the given age

4. **Load Claude memory files into your project.**

   Call `ClaudeMemoryLoader.load_all_memory(project_root)` to read and concatenate all `CLAUDE.md` files in the hierarchy. Use `get_loaded_files()` to inspect which files were included, and `clear_cache()` to force a fresh load on the next call.

   To bootstrap a new project with a default memory file, call `create_default_project_memory(project_root, framework)`. This creates `.claude/CLAUDE.md` under the given `project_root`.

5. **Run the memory test suite.**

   ```
   pytest -k "memory"
   ```

   All tests must pass before you commit changes to this subsystem.

## Verify success

You have completed this task successfully when:

- `is_redis_available()` returns `True` (or your mock backend initializes without error)
- `check_redis_connection()` returns a dict with a positive connection status
- `ClaudeMemoryLoader.load_all_memory()` returns a non-empty string containing the expected memory content
- `MemoryControlPanel.health_check()` returns without errors if you are using the control panel
- `pytest -k "memory"` passes with no failures
