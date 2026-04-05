---
feature: plugin
depth: concept
generated_at: 2026-04-04T13:00:34.171719+00:00
source_hash: d77f635d1744204539648a98bb499be7b81f018d08c49a5f270bbf69bc0595a1
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
