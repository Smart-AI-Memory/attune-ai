---
type: faq
feature: plugin
depth: faq
generated_at: 2026-04-19T18:53:24.485898+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Plugin FAQ

## What is the plugin?

The plugin is a Claude Code extension system that provides skills, hooks, commands, and MCP configuration. It includes a bundled runtime for standalone operation and hooks that automatically format Python files, check help freshness, suggest help when commands fail, and maintain help documentation after git commits.

## When should I use the plugin?

Use the plugin when you need to extend Claude Code's functionality with custom skills, set up automated hooks for file formatting or help maintenance, or configure MCP (Model Context Protocol) behavior. If you're working with standalone operations outside the main Claude Code environment, the bundled runtime lets the plugin operate independently.

## How do I get started with the plugin?

Start with one of these main entry points depending on your goal:

- `plugin/hooks/format_on_save.py` — automatically format Python files after Write/Edit operations
- `plugin/hooks/help_freshness_check.py` — check if help templates are current when sessions start
- `plugin/hooks/help_on_error.py` — suggest relevant help when Bash commands fail

Each module's `main()` function includes documentation about expected inputs and outputs.

## How do I debug plugin issues?

First, run the plugin-specific tests: `pytest -k "plugin" -v`. If the tests pass but your code still fails, add `logger.debug` statements at suspected failure points and re-run with logging enabled to trace the execution flow.

For systematic diagnosis of common problems, check the troubleshooting page for this feature.

## What security validation does the plugin provide?

The plugin includes security functions to validate operations:

- `validate_bash_command()` — checks Bash commands against security policies
- `validate_file_path()` — validates file paths against security policies
- Tool call validation that returns `'allowed': True` for permitted operations

These functions help prevent access to system directories like `/etc`, `/sys`, `/proc`, and other protected paths.

## Where are the plugin source files?

All plugin source files are located in the `plugin/` directory and its subdirectories.

**Tags:** `plugin`, `claude-code`
