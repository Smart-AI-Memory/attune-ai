---
feature: configuration
depth: task
generated_at: 2026-04-06T04:36:34.123286+00:00
source_hash: 6be742830b8d72209e378e70916c649d55dd40a3afdfa434cf328395a1bc4ee3
status: generated
---

# Work with configuration

Use configuration when you need to load, save, or validate Attune AI agent settings and environment variables.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/config/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what configuration
   does today before making changes.
   The primary functions are:
   - `get_attune_env()` in `src/attune/config/env_compat.py` — Get an environment variable, checking ATTUNE_ first then EMPATHY_ fallback.
   - `iter_attune_env_prefix()` in `src/attune/config/env_compat.py` — Yield (middle_part, value) for env vars matching ATTUNE_{prefix}*{suffix}.
   - `get_loader()` in `src/attune/config/loader.py` — Get the global ConfigLoader instance.
   - `load_unified_config()` in `src/attune/config/loader.py` — Convenience function to load unified configuration.
   - `save_unified_config()` in `src/attune/config/loader.py` — Convenience function to save unified configuration.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "configuration"`.

## Key files

- `src/attune/config/**`

## Common modifications

Functions you are most likely to modify:

- `get_attune_env()` in `src/attune/config/env_compat.py`
- `iter_attune_env_prefix()` in `src/attune/config/env_compat.py`
- `get_loader()` in `src/attune/config/loader.py`
- `load_unified_config()` in `src/attune/config/loader.py`
- `save_unified_config()` in `src/attune/config/loader.py`
- `validate_config()` in `src/attune/config/validation.py`
- `get_config()` in `src/attune/config/xml_config.py`
- `set_config()` in `src/attune/config/xml_config.py`
