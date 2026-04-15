---
type: faq
feature: plugin
depth: faq
generated_at: 2026-04-14T15:23:34.645235+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin FAQ

## What is the plugin feature?

The Claude Code plugin system provides hooks, security validation, and automation that runs during your coding sessions. It includes Python file formatting, help system maintenance, error suggestions, and security checks for tool usage.

## When should I use plugins?

You don't directly "use" plugins — they run automatically during your Claude Code sessions. The plugin system activates when you write Python files (auto-formatting), start sessions (help freshness checks), encounter Bash errors (help suggestions), or make git commits (help maintenance).

## What hooks are available?

The plugin system includes four main hooks:

- **PostToolUse format_on_save** — Auto-formats Python files after Write/Edit operations
- **SessionStart help_freshness_check** — Checks if help templates need updates when you start a session
- **PostToolUse help_on_error** — Suggests relevant help when Bash commands fail
- **PostToolUse help_maintenance** — Updates help files after git commits

## How does security validation work?

The plugin includes security policies that validate tool calls before execution. You can check if commands and file paths are allowed using `validate_bash_command()` and `validate_file_path()`. Both return `(True, '')` for allowed operations.

## How do I debug plugin issues?

Run the plugin tests first: `pytest -k "plugin" -v`. If tests pass but you're still having issues, check the stderr output where plugins log their activity. You can also add debug logging to specific hook entry points in the `plugin/hooks/` directory.

## Where are the plugin files located?

All plugin code is in the `plugin/` directory, with hooks in `plugin/hooks/` and the main runtime in `plugin/core/`.

**Tags:** `plugin`, `claude-code`
