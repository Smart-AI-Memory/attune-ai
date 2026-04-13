---
feature: plugin
depth: concept
generated_at: 2026-04-13T18:07:44.279649+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin

## How it works

Claude Code plugin — skills, hooks, commands, and MCP config.

The main entry points are:

- **`main()`** — Read tool result from stdin, format Python files.
- **`main()`** — Check help template freshness on session start.
- **`main()`** — Read PostToolUse payload and suggest help if applicable.
- **`main()`** — Check for stale help after git commit.
- **`validate_bash_command()`** — Validate a Bash command against security policies.

Under the hood, this feature spans 610 source
files covering:

- PostToolUse hook: auto-format Python files after Write/Edit.
- SessionStart hook: check help template freshness.
- PostToolUse hook: suggest help when Bash commands fail.

## What connects to it

This feature relates to: plugin, claude-code.

Other parts of the codebase call into
plugin through these functions:

| Function | Purpose | File |
|----------|---------|------|
| `main()` | Read tool result from stdin, format Python files. | `plugin/hooks/format_on_save.py` |
| `main()` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main()` | Read PostToolUse payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main()` | Check for stale help after git commit. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command()` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
