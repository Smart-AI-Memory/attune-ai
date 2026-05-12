---
feature: memory
depth: task
generated_at: 2026-05-12T20:01:25.921338+00:00
source_hash: f42c657508b8705e9411e006ff4a55425b1657952e6957339000b42557179ccb
status: generated
---

# Work with memory

Use memory when you need to memory subsystem — storage, lookup, and security.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/memory/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what memory
   does today before making changes.
   The primary functions are:
   - `is_redis_available()` in `src/attune/memory/__init__.py` — Check if Redis subsystem is available without importing it.
   - `create_default_project_memory()` in `src/attune/memory/claude_memory.py` — Create a default .claude/CLAUDE.md file for a project.
   - `parse_redis_url()` in `src/attune/memory/config.py` — Parse Redis URL into connection parameters.
   - `get_redis_config()` in `src/attune/memory/config.py` — Get Redis configuration from environment variables (legacy dict API).
   - `get_redis_memory()` in `src/attune/memory/config.py` — Create a RedisShortTermMemory instance with environment-based config.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "memory"`.

## Key files

- `src/attune/memory/**`

## Common modifications

Functions you are most likely to modify:

- `is_redis_available()` in `src/attune/memory/__init__.py`
- `create_default_project_memory()` in `src/attune/memory/claude_memory.py`
- `parse_redis_url()` in `src/attune/memory/config.py`
- `get_redis_config()` in `src/attune/memory/config.py`
- `get_redis_memory()` in `src/attune/memory/config.py`
- `check_redis_connection()` in `src/attune/memory/config.py`
- `get_railway_redis()` in `src/attune/memory/config.py`
- `run_api_server()` in `src/attune/memory/control_panel_api.py`
