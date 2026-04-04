---
feature: cli
depth: task
generated_at: 2026-04-04T02:25:50.507965+00:00
source_hash: 60d629c5d9c90360ec0e4d695e0e6548b4a7742f1575ea77863085ed35e3a4ef
status: generated
---

# Working with Cli

## Overview

Common tasks for modifying or extending cli.

## Key Files

- `src/attune/cli_minimal.py`

- `src/attune/cli_router.py`

- `src/attune/cli_commands/**`


## Common Modifications

Functions you may need to modify:

- `get_version()` in `src/attune/cli_minimal.py`

- `create_parser()` in `src/attune/cli_minimal.py`

- `main()` in `src/attune/cli_minimal.py`

- `is_slash_command()` in `src/attune/cli_router.py`

- `cmd_costs()` in `src/attune/cli_commands/cost_commands.py`

- `cmd_costs_today()` in `src/attune/cli_commands/cost_commands.py`

- `cmd_costs_export()` in `src/attune/cli_commands/cost_commands.py`

- `cmd_costs_reset()` in `src/attune/cli_commands/cost_commands.py`
