---
type: comparison
name: cli-comparison
feature: cli
depth: comparison
generated_at: 2026-06-10T07:07:04.674114+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# Comparison: attune CLI vs HybridRouter

The `attune` CLI and `HybridRouter` are both ways to invoke attune workflows and skills — but they serve different audiences, environments, and interaction patterns.

## Feature comparison

| Feature | `attune` CLI | `HybridRouter` |
|---|---|---|
| **Entry point** | `attune <command>` in a terminal | `HybridRouter.route()` in Python code |
| **Primary audience** | Developers, CI/CD pipelines, shell scripts | Applications embedding attune routing logic |
| **Workflow execution** | `cmd_workflow_run` / `run_workflow_with_exit_code()` | Not applicable — routes to skills, not workflows |
| **Exit-code contract** | Yes — `run_workflow_with_exit_code()` returns `int` for scripting | No — `route()` returns `dict[str, Any]` |
| **Cost tracking** | Yes — `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` | No built-in cost commands |
| **Memory management** | Yes — `cmd_remember`, `cmd_forget`, `cmd_memory_recall`, `cmd_memory_capture`, and others | No |
| **Provider control** | Yes — `cmd_provider_show`, `cmd_provider_set` | No |
| **Telemetry** | Yes — `cmd_telemetry_show`, `cmd_telemetry_savings`, routing stats, model/agent signals | No |
| **Learned routing preferences** | No | Yes — `learn_preference()` stores `RoutingPreference` (keyword, skill, confidence) |
| **Autocomplete suggestions** | No | Yes — `get_suggestions(partial)` |
| **Slash-command detection** | No | Yes — `is_slash_command(text)` |
| **CI/CD use** | Yes — predictable exit codes, JSON output mode | Not designed for it |
| **Interactive / conversational** | No — single-shot invocations | Yes — stateful preferences persist across calls |
| **Setup** | `pip install` + API key, then `attune setup` | Instantiate `HybridRouter(preferences_path=...)` in code |
| **Self-diagnostics** | Yes — `cmd_doctor`, `cmd_validate`, `cmd_features` | No |

## Key tradeoffs

**Exit codes vs. structured dicts.** The CLI's `run_workflow_with_exit_code()` is purpose-built for shell scripting: it returns an `int` that upstream tools (Make, GitHub Actions, bash `set -e`) can act on directly. `HybridRouter.route()` returns a `dict[str, Any]`, which is richer for programmatic consumers but useless as a process exit code.

**Opinionated commands vs. learnable routing.** The CLI ships a fixed set of commands (`cmd_workflow_run`, `cmd_costs`, `cmd_memory_recall`, etc.) whose behavior is defined at install time. `HybridRouter` is designed to adapt: `learn_preference()` stores a `RoutingPreference` with a `confidence` score and `usage_count`, so routing improves as the application accumulates signal.

**Breadth vs. focus.** The CLI covers the full surface — workflows, memory, costs, telemetry, provider settings, curator, patterns, and help. `HybridRouter` does one thing: map user input to a skill invocation, optionally informed by learned preferences.

## Use `attune` CLI when…

- You are running workflows from a shell, Makefile, or CI/CD pipeline and need reliable exit codes.
- You want to track, export, or reset API costs (`cmd_costs_export`, `cmd_costs_reset`).
- You need to manage memory entries directly (`cmd_remember`, `cmd_forget`, `cmd_memory_topics`).
- You are diagnosing a broken environment (`cmd_doctor`, `cmd_validate`).
- You want a self-contained tool that requires no Python integration work.

## Use `HybridRouter` when…

- You are building an application that accepts freeform user input and needs to route it to Claude Code skills programmatically.
- You want routing to improve over time — `learn_preference()` lets you bind keywords to specific skills with tunable `confidence`.
- You need autocomplete UX — `get_suggestions(partial)` returns candidate skill names for a partial input string.
- You are already in Python and returning a `dict[str, Any]` is more useful than a process exit code.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
