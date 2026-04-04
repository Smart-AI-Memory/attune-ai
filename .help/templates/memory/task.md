---
feature: memory
depth: task
generated_at: 2026-04-04T02:25:50.438212+00:00
source_hash: f7be50272674d976f7e23f12d2da9909620b48df295f03bbf3d21d0e9e8b1034
status: generated
---

# Working with Memory

## Overview

Common tasks for modifying or extending memory.

## Key Files

- `src/attune/memory/**`


## Common Modifications

Functions you may need to modify:

- `is_redis_available()` in `src/attune/memory/__init__.py`

- `create_default_project_memory()` in `src/attune/memory/claude_memory.py`

- `parse_redis_url()` in `src/attune/memory/config.py`

- `get_redis_config()` in `src/attune/memory/config.py`

- `get_redis_memory()` in `src/attune/memory/config.py`

- `check_redis_connection()` in `src/attune/memory/config.py`

- `get_railway_redis()` in `src/attune/memory/config.py`

- `run_api_server()` in `src/attune/memory/control_panel_api.py`
