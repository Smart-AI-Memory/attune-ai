---
feature: models
depth: task
generated_at: 2026-06-03T02:40:23.612344+00:00
source_hash: eaf005e9abad245619a99d4824c4b03d726a7b59f62c01ae3437da4261b3bb55
status: generated
---

# Work with models

Use models when you need to llm authentication, provider routing, and tier management.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/models/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what models
   does today before making changes.
   The primary functions are:
   - `cmd_auth_setup()` in `src/attune/models/auth_cli.py` — Run interactive authentication strategy setup.
   - `cmd_auth_status()` in `src/attune/models/auth_cli.py` — Show current authentication strategy configuration.
   - `cmd_auth_reset()` in `src/attune/models/auth_cli.py` — Reset/clear authentication strategy configuration.
   - `cmd_auth_recommend()` in `src/attune/models/auth_cli.py` — Get authentication recommendation for a specific file.
   - `main()` in `src/attune/models/auth_cli.py` — Main CLI entry point.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "models"`.

## Key files

- `src/attune/models/**`

## Common modifications

Functions you are most likely to modify:

- `cmd_auth_setup()` in `src/attune/models/auth_cli.py`
- `cmd_auth_status()` in `src/attune/models/auth_cli.py`
- `cmd_auth_reset()` in `src/attune/models/auth_cli.py`
- `cmd_auth_recommend()` in `src/attune/models/auth_cli.py`
- `main()` in `src/attune/models/auth_cli.py`
- `configure_auth_interactive()` in `src/attune/models/auth_strategy.py`
- `get_auth_strategy()` in `src/attune/models/auth_strategy.py`
- `count_lines_of_code()` in `src/attune/models/auth_strategy.py`
