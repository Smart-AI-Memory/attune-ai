---
type: task
feature: memory
depth: task
generated_at: 2026-04-23T03:30:55.346468+00:00
source_hash: 65cd08d1432d00333db89709ddcd7b9eb6a2277e6649a322b27cb5880d2058a3
status: generated
---

# Work with memory

Use memory when you need to store, retrieve, or secure data across agent sessions or conversations.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/memory/`

## Configure memory backend

1. **Check Redis availability.**
   Use `is_redis_available()` to verify the Redis subsystem is accessible:
   ```python
   from attune.memory import is_redis_available
   if is_redis_available():
       print("Redis backend ready")
   ```

2. **Set up Redis configuration.**
   Call `get_redis_config()` to load settings from environment variables:
   ```python
   from attune.memory.config import get_redis_config
   config = get_redis_config()
   print(f"Redis host: {config['host']}")
   ```

3. **Create memory instance.**
   Use `get_redis_memory()` to initialize a Redis backend:
   ```python
   from attune.memory.config import get_redis_memory
   memory = get_redis_memory()
   ```

## Store and retrieve data

1. **Store data with TTL.**
   Call the `stash()` method with a key, value, and optional TTL:
   ```python
   success = memory.stash("user_preference", {"theme": "dark"}, ttl=3600)
   ```

2. **Retrieve stored data.**
   Use the `retrieve()` method with the same key:
   ```python
   data = memory.retrieve("user_preference")
   if data:
       print(f"Theme: {data['theme']}")
   ```

3. **Clean up data.**
   Delete specific keys when no longer needed:
   ```python
   memory.delete("user_preference")
   ```

## Set up Claude memory integration

1. **Create project memory file.**
   Use `create_default_project_memory()` to initialize CLAUDE.md:
   ```python
   from attune.memory.claude_memory import create_default_project_memory
   create_default_project_memory("/path/to/project", framework="empathy")
   ```

2. **Configure memory loading.**
   Create a `ClaudeMemoryConfig` instance with your requirements:
   ```python
   from attune.memory.claude_memory import ClaudeMemoryConfig
   config = ClaudeMemoryConfig(
       enabled=True,
       load_enterprise=True,
       max_import_depth=3
   )
   ```

3. **Load memory files.**
   Use `ClaudeMemoryLoader` to process all CLAUDE.md files:
   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader
   loader = ClaudeMemoryLoader(config)
   content = loader.load_all_memory("/path/to/project")
   ```

## Run management control panel

1. **Start the control panel.**
   Create a `MemoryControlPanel` instance and check status:
   ```python
   from attune.memory.control_panel import MemoryControlPanel
   panel = MemoryControlPanel()
   status = panel.status()
   print(f"Redis status: {status['redis_status']}")
   ```

2. **Launch API server.**
   Use `run_api_server()` to enable web-based management:
   ```python
   from attune.memory.control_panel_api import run_api_server
   run_api_server(panel, host="localhost", port=8765)
   ```

3. **View memory statistics.**
   Check usage metrics and performance data:
   ```python
   stats = panel.get_statistics()
   print(f"Total patterns: {stats.total_patterns}")
   ```

## Verify setup

Run `pytest -k "memory"` to confirm all memory components work correctly. The tests should pass without errors, indicating proper Redis connectivity and memory operations.
