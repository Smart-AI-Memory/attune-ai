---
type: concept
name: cli-concept
feature: cli
depth: concept
generated_at: 2026-06-02T10:56:02.701360+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI and routing

The attune CLI is the entry point that parses user input, dispatches it to the right command handler, and — through its routing layer — learns which Claude Code skills a user prefers for a given keyword.

## Command groups

`create_parser()` in `attune.cli_minimal` assembles the top-level argument parser. Commands are organized into five groups, each in its own module:

| Group | Module | What it does |
|---|---|---|
| **Cost tracking** | `cli_commands.cost_commands` | Show, export, and reset API cost data (`cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset`) |
| **Memory** | `cli_commands.memory_commands` | Store and retrieve cross-session notes (`cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic`) |
| **Telemetry** | `cli_commands.telemetry_commands` | Inspect routing stats, savings, model usage, and agent signals |
| **Provider** | `cli_commands.provider_commands` | Show or change the active model provider (`cmd_provider_show`, `cmd_provider_set`) |
| **Utility** | `cli_commands.utility_commands` | One-off operations: `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_features`, `cmd_doctor` |

`main()` in `attune.cli_minimal` ties these together: it calls `create_parser()`, runs the matched command function, and returns an integer exit code.

## Routing layer

Not every user input is a structured CLI subcommand. `route_user_input()` in `attune.cli_router` handles free-form text by mapping it to a Claude Code skill invocation. `is_slash_command()` lets callers quickly test whether a string starts with a slash before routing it.

The router that does this work is `HybridRouter`. It holds a list of `RoutingPreference` records and uses them to decide which skill to invoke:

```
user input → HybridRouter.route() → { skill, args, … }
```

`HybridRouter.learn_preference(keyword, skill, args)` writes a new `RoutingPreference` for a keyword. `HybridRouter.get_suggestions(partial)` returns completions for partial input.

## RoutingPreference record

Each learned mapping is a `RoutingPreference` dataclass:

| Field | Type | Meaning |
|---|---|---|
| `keyword` | `str` | Trigger word or phrase |
| `skill` | `str` | Claude Code skill to invoke |
| `args` | `str` | Default arguments passed to the skill |
| `usage_count` | `int` | How many times this preference has fired |
| `confidence` | `float` | Router's confidence in the mapping (default `1.0`) |

Over time, `usage_count` and `confidence` give the router a signal about which preferences are reliable and which might need updating.

## How the pieces fit together

```
attune.cli_minimal.main()
  └─ create_parser()          # builds subcommand tree
  └─ dispatch to cmd_*()      # structured subcommands

attune.cli_router.route_user_input()
  └─ HybridRouter.route()     # free-form text → skill
       └─ RoutingPreference   # per-keyword learned mapping
```

Structured subcommands (everything under `cmd_*`) and the routing layer are independent paths through the same CLI surface. A slash command detected by `is_slash_command()` can bypass the argument parser entirely and go straight to `HybridRouter`.
