---
type: task
name: memory-task
feature: memory
depth: task
generated_at: 2026-06-04T23:45:26.843315+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Work with memory

Use the memory subsystem when you need to store, retrieve, or manage agent memory — including short-term Redis-backed storage, Claude memory file loading, and the enterprise control panel API.

## Prerequisites

- Access to the project source code under `src/attune/memory/`
- A running Redis instance, or the ability to use a mock backend (see `get_redis_memory()`)
- Python environment with project dependencies installed

## Steps

1. **Check whether Redis is available.**
   Call `is_redis_available()` before any Redis-dependent work. This function checks availability without importing the Redis subsystem, so it is safe to call at startup or in conditional logic.

   ```python
   from attune.memory import is_redis_available

   if not is_redis_available():
       # fall back to a mock or file-based backend
       ...
   ```

2. **Obtain a memory backend instance.**
   Choose the factory function that matches your deployment:

   - `get_redis_memory(url=None, use_mock=None)` — creates a `RedisShortTermMemory` instance configured from environment variables. Pass `use_mock=True` to force a mock backend during local development.
   - `get_railway_redis()` — creates a `RedisShortTermMemory` pre-configured for Railway deployments. Raises `OSError` if `REDIS_URL` is not set in the environment.

   ```python
   from attune.memory.config import get_redis_memory

   memory = get_redis_memory()          # uses env vars
   # or
   memory = get_redis_memory(use_mock=True)  # mock for local dev
   ```

3. **Store and retrieve values.**
   Use the `MemoryBackend` protocol methods on the instance you created:

   - `stash(key, value, ttl=None, agent_id=None)` — write a value; returns `True` on success.
   - `retrieve(key, agent_id=None)` — read a value; returns `None` if the key does not exist.
   - `delete(key)` — remove a key; returns `True` on success.
   - `keys(pattern='*')` — list keys matching a glob pattern.

   ```python
   memory.stash("session:42:context", {"user": "alice"}, ttl=3600)
   value = memory.retrieve("session:42:context")
   ```

4. **Load Claude memory files (CLAUDE.md), if needed.**
   To integrate project-level memory files into your agent context, use `ClaudeMemoryLoader`:

   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

   config = ClaudeMemoryConfig(enabled=True, load_project=True, max_import_depth=5)
   loader = ClaudeMemoryLoader(config)
   context_text = loader.load_all_memory(project_root="/path/to/project")
   ```

   To scaffold a new project memory file, call:

   ```python
   from attune.memory.claude_memory import create_default_project_memory

   create_default_project_memory(project_root="/path/to/project")
   ```

   This creates `.claude/CLAUDE.md` in the project root.

5. **Inspect connection health.**
   Call `check_redis_connection()` to get a status dictionary describing the current Redis connection state. Use this in health-check endpoints or startup diagnostics.

   ```python
   from attune.memory.config import check_redis_connection

   status = check_redis_connection()
   print(status)
   ```

6. **Start the Memory Control Panel API (enterprise).**
   If you need the HTTP management API, create a `MemoryControlPanel` and pass it to `run_api_server()`:

   ```python
   from attune.memory.control_panel import MemoryControlPanel, ControlPanelConfig
   from attune.memory.control_panel_api import run_api_server

   config = ControlPanelConfig(redis_host="localhost", redis_port=6379)
   panel = MemoryControlPanel(config)
   run_api_server(panel, host="localhost", port=8765, api_key="secret")
   ```

   The server exposes GET, POST, and DELETE endpoints handled by `MemoryAPIHandler`. Pass `enable_rate_limit=True` (the default) to cap requests via `RateLimiter`.

7. **Run the tests.**
   After any change, run the memory test suite to catch regressions:

   ```bash
   pytest -k "memory"
   ```

## Verify the task succeeded

- `is_redis_available()` returns `True` (or your mock backend initialises without errors).
- `memory.stash(key, value)` returns `True` and `memory.retrieve(key)` returns the same value.
- `check_redis_connection()` returns a dict without error keys.
- `pytest -k "memory"` exits with zero failures.
