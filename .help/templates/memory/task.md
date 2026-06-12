---
type: task
name: memory-task
feature: memory
depth: task
generated_at: 2026-06-12T00:20:52.586192+00:00
source_hash: 439162c85525d4aff627199f05d3f52d259589b86b947c5b2f62b832a0d15fae
status: generated
scaffold_hash: de9d8b9e160093b1f9e12b058655c619120213c3afb90087452e3c0a307ae0a9
---

# Work with memory

Use the memory module when you need agents to stash and retrieve short-term data across sessions, load project-level `CLAUDE.md` context files, or run an HTTP control panel for enterprise memory management.

## Prerequisites

- Redis running and reachable—locally at `localhost:6379` or remotely via `REDIS_URL`—for Redis-backed workflows
- `attune-ai` installed in your Python environment
- (Railway only) Redis service added to your Railway project and `REDIS_URL` exported

## Connect to Redis memory

1. **Check Redis availability.**
   Call `is_redis_available()` before attempting a connection. A return value of `False` means the Redis subsystem is not installed; subsequent calls to `get_redis_memory()` will fail.

   ```python
   from attune.memory import is_redis_available

   if not is_redis_available():
       raise RuntimeError("Redis subsystem not available")
   ```

2. **Create a memory instance.**
   Call `get_redis_memory()` to build a `RedisShortTermMemory` configured from your environment. Pass `url` to override the default endpoint, or set `use_mock=True` to substitute a test double.

   ```python
   from attune.memory import get_redis_memory

   memory = get_redis_memory()
   ```

   For Railway deployments, call `get_railway_redis()` instead. It reads `REDIS_URL` from the Railway environment and raises `OSError` with remediation instructions if the variable is absent.

3. **Verify the connection.**
   Call `check_redis_connection()` and inspect the returned dict for error keys before starting any agent workloads.

   ```python
   from attune.memory import check_redis_connection

   status = check_redis_connection()
   ```

4. **Stash and retrieve values.**
   Use `stash(key, value, ttl, agent_id)` to write and `retrieve(key, agent_id)` to read. Supply `agent_id` to scope entries to a specific agent.

   ```python
   memory.stash("last_query", "What is attune?", ttl=300, agent_id="agent-1")
   result = memory.retrieve("last_query", agent_id="agent-1")
   ```

**You have succeeded when** `check_redis_connection()` returns without an `error` key and `memory.is_connected()` returns `True`.

## Load Claude Code memory files

1. **Configure the loader.**
   Build a `ClaudeMemoryConfig` with `enabled=True`. Toggle `load_enterprise`, `load_user`, and `load_project` to control which hierarchy levels are included. Set `project_root` to pin the search location.

   ```python
   from attune.memory import ClaudeMemoryConfig, ClaudeMemoryLoader

   config = ClaudeMemoryConfig(
       enabled=True,
       load_project=True,
       load_user=True,
       project_root="/path/to/your/project",
   )
   loader = ClaudeMemoryLoader(config)
   ```

2. **Load the files.**
   Call `load_all_memory()` to discover, read, and merge all applicable `CLAUDE.md` files. The return value is combined text ready to inject into a system prompt.

   ```python
   context = loader.load_all_memory()
   ```

3. **Inspect and refresh.**
   Call `get_loaded_files()` to see which files were resolved and in what order. If the files on disk have changed, call `clear_cache()` before the next `load_all_memory()` call.

   ```python
   print(loader.get_loaded_files())
   loader.clear_cache()
   ```

4. **Bootstrap a project with no `CLAUDE.md`.**
   Call `create_default_project_memory(project_root, framework)` to write a starter file at `.claude/CLAUDE.md`. The `framework` argument defaults to `'empathy'`.

   ```python
   from attune.memory import create_default_project_memory

   create_default_project_memory("/path/to/your/project")
   ```

**You have succeeded when** `loader.get_loaded_files()` returns a non-empty list and `load_all_memory()` returns non-empty text.

## Run the memory control panel

1. **Configure the panel.**
   Create a `ControlPanelConfig` pointing at your Redis instance and storage directories, then pass it to `MemoryControlPanel`.

   ```python
   from attune.memory import ControlPanelConfig, MemoryControlPanel

   config = ControlPanelConfig(
       redis_host="localhost",
       redis_port=6379,
       storage_dir="./memdocs_storage",
       audit_dir="./logs",
   )
   panel = MemoryControlPanel(config)
   ```

2. **Start the API server.**
   Call `run_api_server()` with the panel. Set `api_key` to require authentication on every request, and supply `ssl_certfile` and `ssl_keyfile` for TLS. Tune request limits with `rate_limit_requests` and `rate_limit_window`.

   ```python
   from attune.memory import run_api_server

   run_api_server(
       panel,
       host="localhost",
       port=8765,
       api_key="your-secret-key",
       enable_rate_limit=True,
   )
   ```

3. **Confirm the server is healthy.**
   Call `panel.health_check()` before routing production traffic. Use `panel.get_statistics()` to review memory usage and pattern counts, and `print_stats(panel)` for a formatted summary.

   ```python
   print(panel.health_check())
   print(panel.get_statistics())
   ```

**You have succeeded when** `panel.health_check()` returns without error and the server responds on the configured host and port.

## Key files

- `src/attune/memory/__init__.py` — top-level exports and `is_redis_available()`
- `src/attune/memory/config.py` — `get_redis_memory()`, `parse_redis_url()`, `get_redis_config()`, `check_redis_connection()`, `get_railway_redis()`
- `src/attune/memory/claude_memory.py` — `ClaudeMemoryConfig`, `ClaudeMemoryLoader`, `create_default_project_memory()`
- `src/attune/memory/control_panel_api.py` — `MemoryControlPanel`, `ControlPanelConfig`, `run_api_server()`
