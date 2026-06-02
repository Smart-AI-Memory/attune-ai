---
type: comparison
name: cli-comparison
feature: cli
depth: comparison
generated_at: 2026-06-02T10:56:02.747768+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Comparison: CLI vs Claude Code skills

Two ways to drive attune-ai: the `attune` CLI or Claude Code skills invoked through `HybridRouter`. They share the same underlying commands but differ significantly in how you invoke them, what context they see, and which workflows they fit.

## Feature comparison

| Capability | CLI (`attune`) | Claude Code / `HybridRouter` |
|---|---|---|
| Invocation | `attune <command>` subcommands | Natural language or `/skill` syntax via `route_user_input()` |
| Cost tracking | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` | Via MCP tools |
| Memory management | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` | Indirectly through skill calls |
| Telemetry | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, routing stats, model and agent views | Not directly exposed |
| Workflow execution | `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` | Via routed skill invocations |
| Provider control | `cmd_provider_show`, `cmd_provider_set` | Not directly exposed |
| Routing intelligence | Static — you name the subcommand | `HybridRouter` learns `RoutingPreference` entries (keyword, skill, confidence) and improves with `usage_count` |
| Autocomplete / suggestions | Shell completion | `HybridRouter.get_suggestions(partial)` returns ranked completions |
| CI/CD integration | Yes — every command returns an integer exit code | No |
| Context awareness | No — operates on flags and stored state only | Yes — sees conversation history and codebase |
| Interactive follow-up | Manual — run another command | Conversational — the router can propose next steps |
| Setup | `pip install` + API key, then `cmd_setup` / `cmd_validate` / `cmd_doctor` | Plugin install inside Claude Code |

## Key tradeoffs

**CLI is more capable for operational tasks.** The cost, telemetry, provider, and memory command groups are fully exposed only through the CLI. If you need to export cost data (`cmd_costs_export`), inspect routing statistics (`cmd_telemetry_routing_stats`), or reset tracked data (`cmd_costs_reset`), the CLI is the only path.

**`HybridRouter` improves over time; the CLI does not.** Each call to `HybridRouter.learn_preference(keyword, skill, args)` persists a `RoutingPreference` with a `confidence` score and `usage_count`. Over repeated use, the router gets better at guessing your intent from partial input. The CLI always requires the exact subcommand.

**The CLI is the right choice for automation.** Every public command function (`cmd_costs`, `cmd_workflow_run`, etc.) returns an integer exit code, making it composable in shell scripts and CI pipelines. `HybridRouter.route()` returns a `dict`, which is designed for programmatic consumption in a conversational context, not shell chaining.

## When to use the CLI

- You are scripting, running in CI/CD, or need a reliable integer exit code.
- You need direct access to cost tracking (`cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset`), telemetry, provider settings, or memory commands.
- You want deterministic behavior — the exact subcommand always maps to the exact function, with no learned routing in the path.
- You are diagnosing environment issues with `cmd_doctor` or `cmd_validate`.

## When to use `HybridRouter` / Claude Code skills

- You are working interactively inside a Claude Code conversation where follow-up questions and codebase context matter.
- You want the router to learn your shorthand — `learn_preference` lets you bind a keyword to any skill with custom args, and `confidence` improves with `usage_count`.
- You need partial-input completion via `get_suggestions(partial)` rather than a fixed command vocabulary.
- You are building a conversational interface on top of attune-ai and need `route_user_input()` to dispatch dynamically.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
