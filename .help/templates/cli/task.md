---
type: task
feature: cli
depth: task
generated_at: 2026-04-14T15:10:50.363319+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# Work with cli

Use the Attune CLI when you need to interact with the AI system through commands or natural language input that gets intelligently routed to specific skills.

## Prerequisites

- Access to the project source code
- Python environment with the attune package installed
- Basic familiarity with command-line interfaces

## Identify your CLI modification target

1. **Examine the CLI entry point structure.**
   Review `src/attune/cli_minimal.py` to see how the argument parser is configured and how commands are dispatched through the `main()` function.

2. **Check the hybrid routing system.**
   Open `src/attune/cli_router.py` to understand how the `HybridRouter` class routes user input between natural language and slash commands using the `route_user_input()` function.

3. **Locate command implementations.**
   Browse `src/attune/cli_commands/` to find existing command modules like cost tracking (`cmd_costs`, `cmd_costs_today`, `cmd_costs_export`) and help commands.

## Add or modify CLI functionality

1. **For new commands:** Add your command function to the appropriate module in `src/attune/cli_commands/` following the pattern of existing commands that return an integer exit code.

2. **For parser changes:** Modify `create_parser()` in `cli_minimal.py` to add new arguments or subcommands.

3. **For routing changes:** Update the `HybridRouter.route()` method or add new routing preferences using `learn_preference()` to teach the system how to handle specific keywords.

4. **For help system changes:** Modify `cmd_help()` to include new documentation categories from the `_CATEGORIES` tuple (errors, warnings, tips, references).

## Test your changes

1. **Run CLI-specific tests.**
   Execute `pytest -k "cli"` to verify your changes don't break existing functionality.

2. **Test command execution.**
   Run `attune --help` to confirm parser changes appear correctly, and test your specific commands with sample inputs.

3. **Verify routing behavior.**
   Test both slash commands (like `/help`) and natural language inputs to ensure the hybrid router correctly identifies and routes your commands.

You'll know the task succeeded when your new commands execute without errors, return appropriate exit codes, and appear in the help system as expected.
