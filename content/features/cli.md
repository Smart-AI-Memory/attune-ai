---
feature: cli
summary: The attune command-line interface and its natural-language router
tags: [cli, commands]
source_globs:
  - src/attune/cli_minimal.py
  - src/attune/cli_router.py
  - src/attune/cli_commands/**
nav:
  help: cli
  mkdocs:
    how-to: how-to/cli
    architecture: architecture/cli
    reference: reference/cli
---

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

## Quickstart

Check the install and list commands:

```bash
attune --help
attune doctor
```

Run an analysis workflow:

```bash
attune workflow run security-audit
```

## Tasks

### Run a workflow from the CLI

```bash
attune workflow list                 # what's available
attune workflow run code-review      # run one
attune workflow info code-review     # describe it
```

**Verify:** `attune workflow run <slug>` executes the named workflow;
`attune workflow list` enumerates the registered workflows.

### View usage and cost

```bash
attune telemetry show
attune telemetry savings
attune costs today
```

**Verify:** these read the local telemetry store (the same one the
`telemetry` feature writes).

### Route natural-language input in Python

```python
import asyncio

from attune.cli_router import is_slash_command, route_user_input

print(is_slash_command("/security"))          # True
print(is_slash_command("scan my code"))        # False

result = asyncio.run(route_user_input("run a security audit"))
print(result["workflow"], result["confidence"])
```

**Verify:** `is_slash_command` is synchronous; `route_user_input` is
**async** — await it (here via `asyncio.run`). The result dict includes
`workflow`, `skill`, `confidence`, `reasoning`, and `args`.

### List routable workflows

```python
from attune.cli_router import SmartRouter

router = SmartRouter()
print(router.list_workflows())                 # synchronous
```

**Verify:** `SmartRouter.list_workflows()` is synchronous; `route` is
async and `route_sync` is its synchronous counterpart.

## Reference

### Invocation

| Surface | Invocation |
|---------|------------|
| Console script | `attune <command>` (`attune.cli_minimal:main`). |
| Module | `python -m attune.cli_minimal`. |
| Help / health | `attune --help`, `attune doctor`. |

### `attune.cli_router`

| Symbol | Kind | Purpose |
|--------|------|---------|
| `is_slash_command(text) -> bool` | fn (sync) | Is this a `/command`? |
| `route_user_input(user_input, context=None) -> dict` | fn (**async**) | Route text → workflow/skill dict. |
| `SmartRouter` | class | `route` (async) / `route_sync` / `list_workflows` / `get_workflow_info` / `suggest_for_error` / `suggest_for_file`. |
| `HybridRouter` | class | `route`, `get_suggestions`, `learn_preference`. |
| `RoutingPreference` | dataclass | Routing preferences. |

## Comparison

The CLI is one of three front doors to attune:

| | CLI (`attune`) | MCP server | ops dashboard |
|--|----------------|------------|---------------|
| Surface | terminal subcommands | tools in a conversation | local web UI |
| Entry | `attune <command>` | `python -m attune.mcp.server` | `python -m attune.ops` |
| Best for | scripting, terminal use | Claude Code workflows | visual runs/metrics |

The CLI and the MCP server expose overlapping capabilities (run a
workflow, read telemetry) through different surfaces; the router lets
the CLI accept natural language as well as explicit subcommands.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `attune: command not found` | console script not on PATH | reinstall, or use `python -m attune.cli_minimal` | medium |
| `RuntimeWarning: coroutine 'route_user_input' was never awaited` | called `route_user_input` without `await` | it is async — `await` it / `asyncio.run` | high |
| A subcommand errors on args | wrong subcommand or arguments | `attune <group> --help` | low |
| `attune doctor` reports problems | environment/config issue | follow its diagnostics | medium |

### Risk areas

- **`route_user_input` is async.** `is_slash_command` and
  `SmartRouter.list_workflows` are sync; `route` is async (`route_sync`
  is the sync variant).
- **Console script vs module.** If `attune` isn't on PATH, `python -m
  attune.cli_minimal` always works.

### Diagnosis order

1. `attune --help` — is the CLI reachable?
2. `attune doctor` — environment check.
3. `attune <group> --help` — subcommand usage.
4. For routing in Python, remember `route_user_input` is async.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** How do I run the CLI?
  **A:** `attune <command>` (the installed console script) or `python -m
  attune.cli_minimal`. Start with `attune --help` / `attune doctor`.
- **Q:** How do I run a workflow from the terminal?
  **A:** `attune workflow run <slug>` (e.g. `attune workflow run
  code-review`); `attune workflow list` shows the options.
- **Q:** Is the router synchronous?
  **A:** `is_slash_command` and `SmartRouter.list_workflows` are sync;
  `route_user_input` and `SmartRouter.route` are async (use `route_sync`
  for a sync call).
- **Q:** What's the difference between the CLI and the MCP server?
  **A:** Same capabilities, different surface — the CLI is for the
  terminal/scripting; the MCP server exposes them as tools inside Claude
  Code.

## Notes & tips

- **`python -m attune.cli_minimal` is the fallback** when the `attune`
  script isn't on PATH.
- **`attune doctor` first.** It diagnoses most install/config issues.
- **`route_user_input` is async.** `is_slash_command` and
  `list_workflows` are sync.
- **`<group> --help`.** Every command group has its own help.

## Design & extension

### Design decisions

- **argparse with grouped subcommands.** `cli_minimal` keeps a flat,
  dependency-light CLI (`main()` dispatches to `cmd_*` handlers).
- **Routing is separate from dispatch.** `cli_router` decides *what* to
  run from natural language; `cli_minimal` runs explicit subcommands.
- **Sync and async router entries.** `route`/`route_user_input` are
  async for use inside async hosts; `route_sync`/`list_workflows` serve
  synchronous callers.

### Extension points

- **Add a subcommand:** add a `cmd_*` handler and register its parser in
  `cli_minimal.main()`.
- **Influence routing:** `HybridRouter.learn_preference` /
  `RoutingPreference`.
- **Query routing programmatically:** `SmartRouter.route_sync` /
  `list_workflows` / `suggest_for_file`.
