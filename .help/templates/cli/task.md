---
type: task
name: cli-task
feature: cli
depth: task
generated_at: 2026-05-16T06:19:45.804232+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Work with the CLI

Use the attune CLI when you need to add, modify, or debug a CLI command — such as cost tracking, help browsing, memory management, or input routing.

## Prerequisites

- Access to the project source code
- A working Python environment with `pytest` available

## Steps

1. **Identify the command you want to change.**
   Locate the relevant function in the table below. Each function owns a single, named behavior:

   | Function | File | What it does |
   |---|---|---|
   | `cmd_costs()` | `cli_commands/cost_commands.py` | Show cost report for recent period |
   | `cmd_costs_today()` | `cli_commands/cost_commands.py` | Show today's cost summary |
   | `cmd_costs_export()` | `cli_commands/cost_commands.py` | Export cost data to a file |
   | `cmd_costs_reset()` | `cli_commands/cost_commands.py` | Clear all cost tracking data |
   | `cmd_help()` | `cli_commands/help_commands.py` | Handle the `attune help` command |
   | `cmd_remember()` | `cli_commands/memory_commands.py` | Add a lesson to the lessons file |
   | `cmd_forget()` | `cli_commands/memory_commands.py` | Remove a lesson by line number or keyword |
   | `cmd_lessons()` | `cli_commands/memory_commands.py` | List current lessons with line numbers |

   Read the function's docstring, parameters, and return type to confirm it owns the behavior you need.

2. **Review the routing layer.**
   Open `src/attune/cli_router.py` and check how `HybridRouter` dispatches input to the function you identified. If your change affects which skill gets invoked or how preferences are stored, update `route()` or `learn_preference()` accordingly.

3. **Edit the function.**
   Make your changes in the identified file. Match the naming conventions, error-handling style, and logging patterns used by the surrounding functions in that module.

4. **Run the CLI tests.**
   Execute the following command to catch regressions before they reach other developers:

   ```bash
   pytest -k "cli"
   ```

## Key files

- `src/attune/cli_minimal.py` — entry point
- `src/attune/cli_router.py` — `HybridRouter` routing and preference learning
- `src/attune/cli_commands/cost_commands.py` — cost tracking commands
- `src/attune/cli_commands/help_commands.py` — help browsing command
- `src/attune/cli_commands/memory_commands.py` — lessons and memory commands

## Verify your changes

Run `pytest -k "cli"` and confirm all tests pass. Then invoke your changed command directly — for example, `attune help` or `attune costs` — and confirm it produces the expected output with no Python tracebacks.
