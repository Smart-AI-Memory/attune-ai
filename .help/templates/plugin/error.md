---
type: error
feature: plugin
depth: error
generated_at: 2026-04-14T15:22:53.260568+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin errors

Plugin failures occur when the Claude Code plugin system encounters issues with hooks, validation, or file operations during tool execution.

## Common error signatures

- `FileNotFoundError` from format_on_save when Python files are moved or deleted during execution
- `PermissionError` from security_guard when validating paths in protected system directories
- `subprocess.CalledProcessError` from hooks calling external tools like git or formatters
- `JSONDecodeError` when parsing malformed PostToolUse payloads
- `ImportError` when plugin dependencies are missing or incompatible

## Where errors originate

Plugin errors typically emerge from these hook execution points:

- **format_on_save.py**: `main()` reads stdin and formats Python files after Write/Edit operations
- **help_freshness_check.py**: `main()` validates help template timestamps on session start
- **help_on_error.py**: `main()` parses PostToolUse data to suggest relevant help content
- **help_post_commit.py**: `main()` checks for stale help files after git commits
- **security_guard.py**: `validate_bash_command()` and `validate_file_path()` enforce security policies

## How to diagnose

1. **Identify the failing hook.** Check which `plugin/hooks/*.py` file appears in the traceback. Each hook handles a specific trigger (PostToolUse, SessionStart), so the filename indicates what operation failed.

2. **Check validation context.** If `security_guard.py` appears in the trace, examine whether the command or path violates the security policy. System directories like `/etc`, `/proc`, `/sys` are blocked by default.

3. **Verify tool dependencies.** Many hooks call external tools (git, Python formatters). Run the failing command manually to confirm the tool is installed and accessible.

4. **Examine hook input.** For PostToolUse hooks, check that the stdin payload contains valid JSON with expected fields. Malformed tool results cause parsing failures.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
