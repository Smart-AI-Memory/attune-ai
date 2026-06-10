---
type: note
name: cli-note
feature: cli
depth: note
generated_at: 2026-06-10T07:07:04.671376+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# Note: CLI architecture

The `attune` CLI is implemented across two top-level modules and a `cli_commands` package.

- **`attune.cli_minimal`** owns the entry point. `create_parser()` builds the argument parser, and `main()` dispatches to a command handler based on the parsed subcommand. `get_version()` surfaces the installed package version.
- **`attune.cli_router`** handles natural-language and slash-command input. `route_user_input()` and `is_slash_command()` are the primary dispatch functions. `HybridRouter` backs them with a learned-preference layer: it calls `learn_preference()` to associate a keyword with a skill invocation, and `get_suggestions()` to complete partial input. Preferences are stored as `RoutingPreference` records with fields `keyword`, `skill`, `args`, `usage_count`, and `confidence`.
- **`attune.cli_commands`** groups handlers by domain. Each handler receives an `argparse.Namespace` and returns an `int` exit code. The exit-code contract is enforced through `run_workflow_with_exit_code()` in `cli_commands._exit_codes`, which instantiates and executes a workflow class and returns the agreed-upon integer. Command groups include cost tracking (`cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset`), memory (`cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic`), telemetry, provider configuration, workflow management, and utility commands such as `cmd_setup`, `cmd_validate`, and `cmd_doctor`.

`HybridRouter` and the command handlers are independent of each other. The router resolves natural-language input to a skill invocation before any `argparse` parsing occurs; the command handlers run only after `main()` has dispatched a recognized subcommand.
