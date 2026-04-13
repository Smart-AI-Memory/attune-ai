---
feature: plugin
depth: concept
generated_at: 2026-04-13T17:02:17.704285+00:00
source_hash: 87e746872c84d001921b431b15885746de7e8990a689c551172afc6f72cf1c35
status: generated
---

# Plugin

## How it works

Claude Code plugin system provides automated hooks, security validation, and bundled runtime for standalone operation.

The main entry points are:

- **`main()`** — Read tool result from stdin, format Python files.
- **`main()`** — Check help template freshness on session start.
- **`main()`** — Read PostToolUse payload and suggest help if applicable.
- **`main()`** — Check for stale help after git commit.
- **`validate_bash_command()`** — Validate a Bash command against security policies.

Under the hood, this feature spans 610 source
files covering:

- PostToolUse hook: auto-format Python files after Write/Edit operations.
- SessionStart hook: verify help template freshness when Claude starts.
- PostToolUse hook: suggest relevant help documentation when Bash commands fail.
- PostToolUse hook: auto-maintain .help/ directory contents after git commits.
- attune-ai core: bundled runtime environment for standalone plugin operation.

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
