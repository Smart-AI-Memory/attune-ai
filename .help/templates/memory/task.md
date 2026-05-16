---
type: task
name: memory-task
feature: memory
depth: task
generated_at: 2026-05-16T06:14:13.780457+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Work with memory

Use the memory subsystem when you need to store, retrieve, or secure agent memory — whether that means connecting to Redis, loading Claude memory files, or running the Memory Control Panel API.

## Prerequisites

- Read access to `src/attune/memory/`
- Redis available locally or via a `REDIS_URL` environment variable (required for short-term memory and control panel features)
- Python environment with project dependencies installed

## Identify the right entry point

The memory subsystem is divided into focused modules. Choose the function that owns the behavior you need:

| Goal | Function | Module |
|---|---|---|
| Check whether Redis is available | `is_redis_available()` | `src/attune/memory/__init__.py` |
| Create a default `CLAUDE.md` for a project | `create_default_project_memory(project_root, framework)` | `src/attune/memory/claude_memory.py` |
| Parse a Redis URL into connection parameters | `parse_redis_url(url)` | `src/attune/memory/config.py` |
| Read Redis config from environment variables | `get_redis_config()` | `src/attune/memory/config.py` |
| Instantiate a `RedisShortTermMemory` object | `get_redis_memory(url, use_mock)` | `src/attune/memory/config.py` |
| Verify a live Redis connection | `check_redis_connection()` | `src/attune/memory/config.py` |
| Get Redis configured for Railway deployment | `get_railway_redis()` | `src/attune/memory/config.py` |
| Start the Memory Control Panel HTTP API | `run_api_server(panel, host, port, ...)` | `src/attune/memory/control_panel_api.py` |

## Steps

1. **Confirm Redis availability** before writing any memory.

   ```python
   from attune.memory import is_redis_available
   if not is_redis_available():
       raise RuntimeError("Redis is not available. Start Redis or set REDIS_URL.")
   ```

2. **Obtain a memory backend instance** using `get_redis_memory()`. Pass a URL explicitly or let the function read `REDIS_URL` from the environment.

   ```python
   from attune.memory.config import get_redis_memory
   memory = get_redis_memory()          # reads REDIS_URL from env
   # or
   memory = get_redis_memory(url="redis://localhost:6379")
   ```

   For Railway deployments, use `get_railway_redis()` instead. This raises `OSError` if `REDIS_URL` is not set in the Railway environment.

3. **Store and retrieve values** using the `MemoryBackend` protocol methods.

   ```python
   memory.stash("session:42:goal", "draft PR", ttl=3600, agent_id="agent-1")
   value = memory.retrieve("session:42:goal", agent_id="agent-1")
   ```

4. **Load Claude memory files** if your workflow depends on `CLAUDE.md` context. Instantiate `ClaudeMemoryLoader` with a `ClaudeMemoryConfig` and call `load_all_memory()`.

   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

   config = ClaudeMemoryConfig(
       enabled=True,
       load_project=True,
       project_root="/path/to/project",
       max_import_depth=5,
   )
   loader = ClaudeMemoryLoader(config)
   context = loader.load_all_memory()
   ```

   To create a default `CLAUDE.md` for a project that does not have one yet:

   ```python
   from attune.memory.claude_memory import create_default_project_memory
   create_default_project_memory("/path/to/project", framework="empathy")
   ```

5. **Start the Memory Control Panel API** when you need HTTP access to memory statistics, pattern management, or audit logs.

   ```python
   from attune.memory.control_panel_api import run_api_server
   from attune.memory.control_panel import MemoryControlPanel

   panel = MemoryControlPanel()
   run_api_server(panel, host="localhost", port=8765, api_key="my-secret-key")
   ```

6. **Run the memory test suite** to catch regressions before your changes reach other developers.

   ```bash
   pytest -k "memory"
   ```

## Verify the task succeeded

- `is_redis_available()` returns `True`.
- `check_redis_connection()` returns a dict with a `"status"` key equal to `"ok"`.
- `memory.retrieve(key, agent_id=...)` returns the value you passed to `memory.stash(...)`.
- `loader.get_loaded_files()` lists the `CLAUDE.md` paths that were found and parsed.
- The API server responds to `GET /health` (or equivalent) without error when started with `run_api_server()`.
- `pytest -k "memory"` passes with no failures.
