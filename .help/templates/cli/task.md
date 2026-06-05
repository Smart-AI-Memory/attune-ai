---
feature: cli
depth: task
generated_at: 2026-06-05T16:32:09.116036+00:00
source_hash: 198ad869d0b029e3926d86fd51b53c7d1a800d65335cb982b9331b5ee6c9bcaa
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
- `run_workflow_with_exit_code()` in `src/attune/cli_commands/_exit_codes.py`
- `cmd_costs()` in `src/attune/cli_commands/cost_commands.py`
- `cmd_costs_today()` in `src/attune/cli_commands/cost_commands.py`
