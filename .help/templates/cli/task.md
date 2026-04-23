---
type: task
feature: cli
depth: task
generated_at: 2026-04-23T03:31:59.645342+00:00
source_hash: 95afb1e38daa117bab7e14bf58b614da535d484b24b1dd072c4750e232202196
status: generated
---

# Work with cli

Use the Attune CLI when you need to route user input between natural language and skill commands, track costs, or access help documentation from the command line.

## Prerequisites

- Access to the project source code
- Python environment with attune package installed
- Familiarity with the CLI module structure in `src/attune/`

## Configure the CLI entry point

1. **Set up the main parser** by modifying `create_parser()` in `cli_minimal.py`:
   - Add subcommands for new functionality
   - Define argument groups and options
   - Set default values and help text

2. **Route commands** through the `main()` function:
   - Handle argument parsing
   - Dispatch to appropriate command handlers
   - Return proper exit codes

## Add command functionality

1. **Create command handlers** in the appropriate module:
   - Cost commands: Use `cmd_costs()`, `cmd_costs_today()`, `cmd_costs_export()`, or `cmd_costs_reset()` in `cost_commands.py`
   - Help commands: Use `cmd_help()` in the help module
   - Memory commands: Implement handlers for learning and recall

2. **Implement hybrid routing** using the `HybridRouter` class:
   ```python
   router = HybridRouter(preferences_path="path/to/prefs")
   result = router.route(user_input, context)
   ```

3. **Handle slash commands** by checking input with `is_slash_command()` before routing.

## Test the implementation

1. **Run targeted tests** with:
   ```bash
   pytest -k "cli"
   ```

2. **Test command routing** by running:
   ```bash
   attune help
   attune costs today
   attune "your natural language query"
   ```

3. **Verify routing preferences** are learned and applied correctly for repeated commands.

## Verification

Your CLI implementation works when:
- All subcommands execute without errors
- Natural language input routes to appropriate skills
- Cost tracking commands return accurate data
- Help commands display relevant documentation
- The router learns and suggests command preferences over time
