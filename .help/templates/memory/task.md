---
type: task
feature: memory
depth: task
generated_at: 2026-04-14T15:04:42.142088+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Work with memory

Use the memory subsystem when you need to store agent state, load Claude Code memory files, or manage distributed memory backends across sessions.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/memory/`
- Redis server (for distributed backends)

## Configure memory backends

1. **Check Redis availability** before connecting to distributed backends:
   ```python
   from attune.memory import is_redis_available

   if is_redis_available():
       # Use Redis backend
   else:
       # Fall back to file-based memory
   ```

2. **Set up Redis connection** using environment variables:
   ```bash
   export REDIS_URL="redis://localhost:6379"
   ```

3. **Create a memory backend instance**:
   ```python
   from attune.memory import get_redis_memory

   memory = get_redis_memory()  # Uses REDIS_URL from environment
   ```

4. **Verify the connection** is working:
   ```python
   if memory.is_connected():
       stats = memory.get_stats()
       print(f"Connected to Redis: {stats}")
   ```

## Store and retrieve data

1. **Store short-term data** with automatic expiration:
   ```python
   memory.stash("user_context", {"session": "abc123"}, ttl=3600)
   ```

2. **Retrieve stored data** by key:
   ```python
   context = memory.retrieve("user_context")
   if context:
       print(f"Found context: {context}")
   ```

3. **Search across stored patterns** (if using searchable backend):
   ```python
   from attune.memory.backends import SearchableMemoryBackend

   if isinstance(memory, SearchableMemoryBackend):
       results = memory.search("error handling", limit=5)
   ```

## Load Claude Code memory files

1. **Create a memory loader** with your project configuration:
   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

   config = ClaudeMemoryConfig(
       enabled=True,
       project_root="/path/to/project",
       max_import_depth=3
   )
   loader = ClaudeMemoryLoader(config)
   ```

2. **Load all CLAUDE.md files** from the project hierarchy:
   ```python
   memory_content = loader.load_all_memory()
   print(f"Loaded {len(loader.get_loaded_files())} memory files")
   ```

3. **Create default memory structure** for new projects:
   ```python
   from attune.memory.claude_memory import create_default_project_memory

   create_default_project_memory("/path/to/project", framework="empathy")
   ```

## Set up the control panel

1. **Configure the control panel** for memory management:
   ```python
   from attune.memory.control_panel import MemoryControlPanel, ControlPanelConfig

   config = ControlPanelConfig(
       redis_host="localhost",
       redis_port=6379,
       auto_start_redis=True
   )
   panel = MemoryControlPanel(config)
   ```

2. **Start the API server** for remote management:
   ```python
   from attune.memory.control_panel_api import run_api_server

   run_api_server(
       panel=panel,
       host="0.0.0.0",
       port=8765,
       api_key="your-secure-key"
   )
   ```

3. **Check system health** to verify everything is working:
   ```python
   health = panel.health_check()
   if health["status"] == "healthy":
       print("Memory system is operational")
   ```

## Verify success

Your memory integration is working when:
- `memory.is_connected()` returns `True`
- You can store and retrieve data without errors
- Claude memory files load successfully with `loader.get_loaded_files()` showing expected paths
- The control panel API responds to health checks with status "healthy"

## Key files

- `src/attune/memory/backends.py` — Memory backend protocols and interfaces
- `src/attune/memory/claude_memory.py` — Claude Code memory file loading
- `src/attune/memory/config.py` — Redis configuration and connection management
- `src/attune/memory/control_panel.py` — Enterprise memory management interface
- `src/attune/memory/control_panel_api.py` — HTTP API for remote control panel access
