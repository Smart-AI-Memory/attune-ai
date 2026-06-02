---
type: task
name: cli-task
feature: cli
depth: task
generated_at: 2026-06-02T10:56:02.708047+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Work with the attune CLI

Use the attune CLI when you need to run cost reports, manage memory, inspect telemetry, or control routing behavior from the command line.

## Prerequisites

- Access to the project source code
- `attune` installed and available on your PATH (run `attune --version` to confirm)
- Familiarity with `src/attune/cli_minimal.py` as the main entry point

## Run built-in CLI commands

The CLI is organized into command groups. Each command is a standalone function that accepts an `argparse.Namespace` and returns an integer exit code.

**Cost commands** — track and export API spending:

| Command | Function | What it does |
|---|---|---|
| `attune costs` | `cmd_costs()` | Show a cost report for the recent period |
| `attune costs today` | `cmd_costs_today()` | Show today's cost summary |
| `attune costs export` | `cmd_costs_export()` | Export cost data to a file |
| `attune costs reset` | `cmd_costs_reset()` | Clear all cost tracking data |

**Memory commands** — persist and retrieve lessons across sessions:

| Command | Function | What it does |
|---|---|---|
| `attune remember` | `cmd_remember()` | Add a lesson to the lessons file |
| `attune forget` | `cmd_forget()` | Remove a lesson by line number or keyword |
| `attune lessons` | `cmd_lessons()` | List current lessons with line numbers |
| `attune memory capture` | `cmd_memory_capture()` | Save content to personal cross-session memory |
| `attune memory recall` | `cmd_memory_recall()` | Search personal cross-session memory |
| `attune memory topics` | `cmd_memory_topics()` | List available memory topics |
| `attune memory forget-topic` | `cmd_memory_forget_topic()` | Remove an entire memory topic |

**Utility commands** — inspect and configure attune itself:

| Command | Function | What it does |
|---|---|---|
| `attune setup` | `cmd_setup()` | Run interactive first-time setup |
| `attune validate` | `cmd_validate()` | Validate the current configuration |
| `attune doctor` | `cmd_doctor()` | Diagnose common environment problems |
| `attune features` | `cmd_features()` | List available features |
| `attune version` | `cmd_version()` | Print the installed version |

## Extend or modify a CLI command

1. **Identify the responsible function.** Each command maps to a single function in one of the modules under `src/attune/cli_commands/`. For example, `cmd_costs_export()` lives in `src/attune/cli_commands/cost_commands.py`. Read its signature, docstring, and return type to confirm it owns the behavior you need.

2. **Open the correct module.** The modules and their responsibilities are:
   - `cost_commands.py` — cost reporting and export
   - `memory_commands.py` — lessons and cross-session memory
   - `help_commands.py` — the `attune help` command
   - `provider_commands.py` — provider selection and display
   - `telemetry_commands.py` — telemetry, routing stats, and model signals
   - `utility_commands.py` — setup, validation, and diagnostics
   - `workflow_commands.py` — workflow listing and execution

3. **Edit the function body.** Keep the function signature (`args: Namespace`) and return type (`int`) unchanged. Return `0` on success and a non-zero integer on failure, consistent with the rest of the module.

4. **Update the parser if you add a new flag.** New arguments must be registered in `src/attune/cli_minimal.py` via `create_parser()`. Run `attune help` afterward to confirm the flag appears in the help output.

5. **Run the related tests.** Target CLI tests with:
   ```
   pytest -k "cli"
   ```

## Configure routing behavior

The `HybridRouter` in `src/attune/cli_router.py` maps user input to skill invocations. You can teach it a new keyword-to-skill mapping at runtime:

```python
from attune.cli_router import HybridRouter

router = HybridRouter()
router.learn_preference(keyword="deploy", skill="deploy_skill", args="--env prod")
```

Each learned preference is stored as a `RoutingPreference` with the fields `keyword`, `skill`, `args`, `usage_count`, and `confidence`. To retrieve completions for a partial input, call `router.get_suggestions(partial)`.

To route a single input string directly without constructing a router instance, use the module-level helper:

```python
from attune.cli_router import route_user_input

result = route_user_input("show costs", context={"user": "alice"})
```

## Verify the task worked

After running or modifying a command, confirm success by checking:

- The command exits with code `0` (all `cmd_*` functions return `0` on success).
- `attune costs` or `attune lessons` produces updated output that reflects your change.
- `pytest -k "cli"` passes with no failures or errors.
- `attune doctor` reports no new issues introduced by your change.

## Key files

- `src/attune/cli_minimal.py` — entry point and parser (`main()`, `create_parser()`)
- `src/attune/cli_router.py` — routing logic (`HybridRouter`, `route_user_input()`)
- `src/attune/cli_commands/` — one module per command group

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 18 | error | `attune --version` — flag not found in `attune --help`  Detected against attune 5.10.0 (installed in active venv). If you are regenerating against a different version, verify the flag exists in that version's `attune --help`. To override:   - One-off:  attune-author generate FEATURE --skip-check check_cli_refs   - Per file: [tool.attune-author.fact-check.skip]               ".help/templates/cli/task.md" = ["check_cli_refs"] |
