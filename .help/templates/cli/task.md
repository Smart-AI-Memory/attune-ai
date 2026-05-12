---
feature: cli
depth: task
generated_at: 2026-05-12T20:01:25.945974+00:00
source_hash: 9b280c902cb899cdf4292fc1221ba1b77cb6c199e12090acd143692bd7817bd6
status: generated
---

# Work with cli

Use cli when you need to command-line interface and routing.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/cli_minimal.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what cli
   does today before making changes.
   The primary functions are:
   - `get_version()` in `src/attune/cli_minimal.py` — Get package version.
   - `create_parser()` in `src/attune/cli_minimal.py` — Create the argument parser.
   - `main()` in `src/attune/cli_minimal.py` — Main entry point.
   - `route_user_input()` in `src/attune/cli_router.py` — Quick routing helper.
   - `is_slash_command()` in `src/attune/cli_router.py` — Check if text is a slash command.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "cli"`.

## Key files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Common modifications

Functions you are most likely to modify:

- `get_version()` in `src/attune/cli_minimal.py`
- `create_parser()` in `src/attune/cli_minimal.py`
- `main()` in `src/attune/cli_minimal.py`
- `route_user_input()` in `src/attune/cli_router.py`
- `is_slash_command()` in `src/attune/cli_router.py`
- `cmd_costs()` in `src/attune/cli_commands/cost_commands.py`
- `cmd_costs_today()` in `src/attune/cli_commands/cost_commands.py`
- `cmd_costs_export()` in `src/attune/cli_commands/cost_commands.py`
