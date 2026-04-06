---
feature: cli
depth: task
generated_at: 2026-04-06T04:33:15.002130+00:00
source_hash: 60d629c5d9c90360ec0e4d695e0e6548b4a7742f1575ea77863085ed35e3a4ef
status: generated
---

# Work with cli

Use the Attune AI CLI when you need to interact with the system through command-line interface or route user input between skills and natural language processing.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/cli_minimal.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what the CLI hybrid router
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
