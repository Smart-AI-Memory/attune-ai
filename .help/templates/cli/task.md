---
type: task
feature: cli
depth: task
generated_at: 2026-05-04T02:34:05.644870+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Work with cli

Use the attune CLI when you need to access cost tracking, documentation help, or memory management from the command line.

## Prerequisites

- Access to the project source code
- Basic familiarity with Python command-line argument parsing
- Understanding of the attune project structure

## Steps

1. **Identify the command category you need to modify.**
   The CLI is organized into three main areas:
   - Cost commands (`src/attune/cli_commands/cost_commands.py`) for tracking usage costs
   - Help commands (`src/attune/cli_commands/help_commands.py`) for browsing documentation
   - Memory commands (`src/attune/cli_commands/memory_commands.py`) for managing lessons and cross-session memory

2. **Locate the specific command function.**
   Each CLI command maps to a single function with a `cmd_` prefix:
   - `cmd_costs()` — Show cost report for recent period
   - `cmd_costs_today()` — Show today's cost summary
   - `cmd_costs_export()` — Export cost data to file
   - `cmd_costs_reset()` — Clear all cost tracking data
   - `cmd_help()` — Handle the `attune help` command
   - `cmd_remember()` — Add a lesson to the lessons file
   - `cmd_forget()` — Remove a lesson by line number or keyword
   - `cmd_lessons()` — List current lessons with line numbers

3. **Review the function signature and existing logic.**
   Each command function takes an `argparse.Namespace` object and returns an integer exit code. Read the function's docstring and examine how it processes arguments and handles errors.

4. **Implement your changes.**
   Follow the established patterns in each file:
   - Use the same argument validation approach
   - Return `0` for success, non-zero for errors
   - Handle exceptions gracefully with appropriate error messages

5. **Test your command.**
   Run the modified command directly: `python -m attune <your-command>` to verify it works as expected.

## Verify success

Your CLI modification works correctly when:
- The command executes without Python errors
- The exit code is `0` for successful operations
- Error messages are clear and actionable
- The command behaves consistently with other attune CLI commands
