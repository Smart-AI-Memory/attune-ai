---
type: task
name: cli-task
feature: cli
depth: task
generated_at: 2026-06-22T09:48:39.757537+00:00
source_hash: 164b677043cfbe05cdc85850c811ec14af92dabac3c48dced21fedf0c3c58146
status: generated
---

# Work with the attune CLI

Use the attune CLI when you need to run workflows, manage memory and costs, or extend command behavior from the terminal.

## Prerequisites

- Access to the project source code
- Python environment with attune installed
- Familiarity with `src/attune/cli_minimal.py` as the CLI entry point

## Identify the right command module

The CLI is organized into focused modules. Before writing or modifying any code, confirm which module owns the behavior you need:

| Module | Responsibility |
|---|---|
| `cli_commands/_exit_codes.py` | Executes a workflow class and returns a contract exit code via `run_workflow_with_exit_code()` |
| `cli_commands/cost_commands.py` | Cost reporting and reset: `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` |
| `cli_commands/curator.py` | Renders the project briefing via `cmd_curator()` |
| `cli_commands/help_commands.py` | Handles `attune help` via `cmd_help()` |
| `cli_commands/memory_agent.py` | Runs a single-shot agent with Redis-backed memory via `cmd_memory_agent()` |
| `cli_commands/memory_commands.py` | Lesson and memory management: `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` |
| `cli_commands/pattern_review.py` | Pattern lifecycle: `cmd_patterns_review`, `cmd_patterns_promote`, `cmd_patterns_reject` |
| `cli_commands/provider_commands.py` | Provider inspection and switching: `cmd_provider_show`, `cmd_provider_set` |
| `cli_commands/telemetry_commands.py` | Telemetry, savings, routing stats, and model/agent signals |
| `cli_commands/utility_commands.py` | Setup, validation, version, features, and diagnostics via `cmd_doctor()` |
| `cli_commands/workflow_commands.py` | Workflow listing, inspection, and execution: `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` |
| `cli_router.py` | Routes free-text input to skill invocations via `HybridRouter` |

## Add or modify a CLI command

1. **Open the module** that owns the relevant command (see table above). Read the function signature, docstring, and return type to confirm the function handles what you need.

2. **Edit the command function.** Each command function accepts an `argparse.Namespace` argument and returns an `int` exit code. Add your logic inside the matching `cmd_*` function.

3. **Register new commands in the parser.** If you are adding a new subcommand, open `src/attune/cli_minimal.py` and call `create_parser()` to locate where subparsers are registered. Add your subcommand there, pointing its `set_defaults(func=...)` to your new `cmd_*` function.

4. **Run the related tests** to catch regressions before they reach other developers:

   ```
   pytest -k "cli"
   ```

## Teach the router a new preference

Use `HybridRouter` from `attune.cli_router` when you want the router to map a keyword to a specific skill automatically.

1. **Instantiate the router:**

   ```python
   from attune.cli_router import HybridRouter

   router = HybridRouter()
   ```

2. **Register a keyword preference** with `learn_preference()`:

   ```python
   router.learn_preference(keyword="costs", skill="cost_report", args="--today")
   ```

   This creates a `RoutingPreference` with the fields `keyword`, `skill`, `args`, `usage_count`, and `confidence`.

3. **Check autocomplete suggestions** for a partial string:

   ```python
   suggestions = router.get_suggestions("cos")
   ```

4. **Route a free-text input** and inspect the result:

   ```python
   result = router.route("show me today's costs")
   ```

## Verify your changes

After editing a command or registering a routing preference, confirm the change works end-to-end:

1. Run `attune --help` and verify your subcommand appears in the output.
2. Run the subcommand directly — for example, `attune costs` — and confirm it exits with code `0` on success.
3. For routing changes, call `router.get_suggestions()` with a partial keyword and confirm your new keyword appears in the returned list.
4. Run `pytest -k "cli"` and confirm all tests pass with no new failures.

## Key files

- `src/attune/cli_minimal.py` — entry point; defines `main()` and `create_parser()`
- `src/attune/cli_router.py` — `HybridRouter`, `route_user_input()`, `RoutingPreference`
- `src/attune/cli_commands/` — one module per command group
