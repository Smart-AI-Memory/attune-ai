---
type: faq
name: cli-faq
feature: cli
depth: faq
status: manual
---

# CLI FAQ

## What does the CLI feature cover?

It covers two things: the command-line interface (all `attune` subcommands) and the routing layer that maps user input to the right skill or workflow.

## How do I run the CLI?

Call `main()` from `attune.cli_minimal`. It accepts an optional `argv` list; when omitted it reads from `sys.argv`. Every command returns an integer exit code.

## How does routing work?

`route_user_input()` in `attune.cli_router` takes a string of user input and an optional context dict, then returns a routing decision as a dict. **It is async** — `await` it (e.g. `asyncio.run(route_user_input(text))`). `is_slash_command` and `SmartRouter.list_workflows` are synchronous; `SmartRouter.route_sync` is the synchronous routing call. For more control, instantiate `HybridRouter` directly — it lets you call `route()`, teach it new preferences with `learn_preference()`, and get tab-completion candidates with `get_suggestions()`.

## What is a `RoutingPreference`?

A `RoutingPreference` is a dataclass that records one learned routing rule. Its fields are `keyword`, `skill`, `args` (default `''`), `usage_count` (default `0`), and `confidence` (default `1.0`). The router accumulates these over time to improve its suggestions.

## How do I tell whether a string is a slash command?

Call `is_slash_command(text)` from `attune.cli_router`. It returns a boolean.

## Which subcommands are available?

The CLI is organized into groups:

| Group | Subcommands |
|---|---|
| **Costs** | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` |
| **Memory** | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` |
| **Telemetry** | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals` |
| **Workflows** | `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` |
| **Patterns** | `cmd_patterns_review`, `cmd_patterns_promote`, `cmd_patterns_reject` |
| **Providers** | `cmd_provider_show`, `cmd_provider_set` |
| **Utility** | `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_features`, `cmd_doctor` |

## What exit codes does `attune workflow run` return?

`run_workflow_with_exit_code()` in `cli_commands._exit_codes` instantiates and executes a workflow, then returns the contract exit code as an integer. The specific values depend on the workflow result; check `cli_commands._exit_codes` for the full contract.

## How do I debug a failing command?

Run the related tests first with `pytest -k "cli" -v`. If the tests pass but your code still fails, add a `logger.debug` statement at the suspected failure point and re-run with logging enabled. For symptom-based issues, see the troubleshooting page for this feature.

## Where are the source files?

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
