---
feature: plugin
depth: concept
generated_at: 2026-04-04T02:25:50.650004+00:00
source_hash: 91035b6062c35b9c5a02a46b975ee4d920fbf79b8c3cad1575709d661c5d2cde
status: generated
---

# Plugin

## What

Claude Code plugin — skills, hooks, commands, and MCP config

## Why

This feature provides plugin functionality for the project.

## How

Key functions:

- `main()` — Read tool result from stdin, format Python files.

- `main()` — Check help template freshness on session start.

- `main()` — Read PostToolUse payload and suggest help if applicable.

- `main()` — Check for stale help after git commit.

- `validate_bash_command()` — Validate a Bash command against security policies.
