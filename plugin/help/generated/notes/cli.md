---
name: cli
source: content/features/cli.md
tags:
- cli
- commands
type: note
---

# The attune command-line interface and its natural-language router

## Overview

The `attune` command-line interface is the terminal front door to the
framework. It has two layers:

- **The CLI itself** (`attune.cli_minimal`) — an argparse program with
  grouped subcommands (`workflow`, `telemetry`, `costs`, `auth`,
  `memory`, `doctor`, `setup`, …). The `attune` console script runs its
  `main()`.
- **The natural-language router** (`attune.cli_router`) — turns free
  text or a `/slash` command into a workflow/skill choice
  (`route_user_input`, `is_slash_command`, `SmartRouter`,
  `HybridRouter`).

You invoke it as `attune <command>` (the installed console script) or
`python -m attune.cli_minimal`.

## Concepts

### Invocation

The packaged entry point is `attune = attune.cli_minimal:main`
(`[project.scripts]`), so `attune <command>` runs the CLI; `python -m
attune.cli_minimal` is equivalent. `attune --help` lists the commands;
`attune doctor` checks the install.

### Command groups

`cli_minimal` registers grouped subcommands, each dispatched to a
`cmd_*` handler:

- `workflow` — `list`, `info`, `run` (run an analysis workflow).
- `telemetry` — `show`, `savings`, `export`, `enable`/`disable`,
  `models`, `agents`, `signals`.
- `costs` — `today`, `export`, `reset`.
- `auth` — `setup`, `reset`; `provider` — `show`, `set`.
- memory — `capture`, `recall`, `topics`, `forget-topic`; plus
  `remember` / `forget` / `lessons`.
- `patterns` — `review`, `promote`, `reject`.
- standalone — `setup`, `doctor`, `features`, `validate`, `version`,
  `help-docs`.

### The natural-language router

`attune.cli_router` maps user input to a workflow or skill.
`is_slash_command(text)` tells a `/command` from prose.
`route_user_input(user_input, context=None)` is **async** and returns a
routing dict (`workflow`, `skill`, `confidence`, `reasoning`, `args`,
`secondary_workflows`, `type`, `source`, …). `SmartRouter` exposes
`route` (async) / `route_sync` (sync) / `list_workflows` /
`get_workflow_info` / `suggest_for_error` / `suggest_for_file`;
`HybridRouter` adds `get_suggestions` and `learn_preference`;
`RoutingPreference` carries routing preferences.

## Notes & tips

- **`python -m attune.cli_minimal` is the fallback** when the `attune`
  script isn't on PATH.
- **`attune doctor` first.** It diagnoses most install/config issues.
- **`route_user_input` is async.** `is_slash_command` and
  `list_workflows` are sync.
- **`<group> --help`.** Every command group has its own help.
