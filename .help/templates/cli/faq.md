---
type: faq
feature: cli
depth: faq
generated_at: 2026-04-14T15:12:12.938907+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI FAQ

## What is the Attune CLI?

The Attune CLI is a hybrid command-line interface that combines traditional skill-based commands with natural language routing, allowing you to interact with AI features through both structured commands and conversational input.

## When should I use the CLI versus other interfaces?

Use the CLI when you want to:
- Access cost tracking and reporting features
- Browse help documentation from the command line
- Route natural language queries to appropriate AI skills
- Work with Attune features in a terminal environment

## How do I get started with the CLI?

Start with the `main()` function in `src/attune/cli_minimal.py`, which serves as the primary entry point. You can also use `create_parser()` to understand available command options, or `get_version()` to check your installation.

## What cost tracking commands are available?

The CLI provides several cost management commands:
- `cmd_costs()` — Show cost reports for recent periods
- `cmd_costs_today()` — Display today's cost summary
- `cmd_costs_export()` — Export cost data to a file
- `cmd_costs_reset()` — Clear all cost tracking data

## How does the hybrid routing work?

The `HybridRouter` class learns your preferences over time. Use `route_user_input()` for quick routing, or create a router instance to access preference learning with `learn_preference()` and command suggestions with `get_suggestions()`.

## How do I check if input is a slash command?

Use the `is_slash_command()` function to determine if text follows the slash command format before processing it through the router.

## How do I debug CLI issues?

Run `pytest -k "cli" -v` to check if the CLI tests pass. If they do but you're still having issues, add `logger.debug` statements at suspected failure points and re-run with logging enabled.

## Where can I find the source code?

The CLI code is organized across:
- `src/attune/cli_minimal.py` — Core CLI functionality
- `src/attune/cli_router.py` — Hybrid routing system
- `src/attune/cli_commands/` — Individual command modules

**Tags:** `cli`, `commands`
