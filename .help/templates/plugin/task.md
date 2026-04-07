---
feature: plugin
depth: task
generated_at: 2026-04-06T16:05:32.038115+00:00
source_hash: 46bc4dc7cf2e9c03097725e0f7d8034bd661bccf3ff72ed40d1e5832e5000dd4
status: generated
---

# Work with plugin

Use plugin when you need to claude code plugin — skills, hooks, commands, and mcp config.

## Prerequisites

- Access to the project source code
- Familiarity with the files under plugin/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what plugin
   does today before making changes.
   The primary functions are:
   - `main()` in `plugin/hooks/format_on_save.py` — Read tool result from stdin, format Python files.
   - `main()` in `plugin/hooks/help_freshness_check.py` — Check help template freshness on session start.
   - `main()` in `plugin/hooks/help_on_error.py` — Read PostToolUse payload and suggest help if applicable.
   - `main()` in `plugin/hooks/help_post_commit.py` — Check for stale help after git commit.
   - `validate_bash_command()` in `plugin/hooks/security_guard.py` — Validate a Bash command against security policies.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "plugin"`.

## Key files

- `plugin/**`

## Common modifications

Functions you are most likely to modify:

- `main()` in `plugin/hooks/format_on_save.py`
- `main()` in `plugin/hooks/help_freshness_check.py`
- `main()` in `plugin/hooks/help_on_error.py`
- `main()` in `plugin/hooks/help_post_commit.py`
- `validate_bash_command()` in `plugin/hooks/security_guard.py`
- `validate_file_path()` in `plugin/hooks/security_guard.py`
- `main()` in `plugin/hooks/security_guard.py`
- `main()` in `plugin/hooks/welcome.py`
