---
type: error
feature: plugin
depth: error
generated_at: 2026-04-19T18:52:40.902622+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Plugin errors

Plugin failures occur when Claude Code's runtime hooks, security policies, or MCP configuration encounter unexpected conditions during tool execution or session initialization.

## Common error signatures

- **`FileNotFoundError`** — Help template missing during freshness check or post-commit maintenance
- **`json.JSONDecodeError`** — Malformed PostToolUse payload in help-on-error hook
- **`subprocess.CalledProcessError`** — Python formatter (black/ruff) fails in format-on-save hook
- **`PermissionError`** — Security guard blocks access to system directories like `/etc`, `/sys`, `/proc`
- **`ValueError`** — Invalid file path or bash command rejected by validation policies
- **`ImportError`** — Missing formatter dependency (black, ruff, isort) when processing Python files

## Where errors originate

Plugin errors stem from these main execution paths:

- **`main()` in format_on_save.py** — Reads stdin for tool results and runs Python formatters
- **`main()` in help_freshness_check.py** — Validates help template currency at session start
- **`main()` in help_on_error.py** — Parses PostToolUse events and suggests relevant help
- **`main()` in help_post_commit.py** — Detects stale help files after git commits
- **`validate_bash_command()` in security_guard.py** — Enforces command security policies
- **`validate_file_path()` in security_guard.py** — Blocks access to protected filesystem areas

## How to diagnose

1. **Check which hook failed.** Plugin hooks run at specific trigger points — format-on-save after Write/Edit tools, help checks at session start, security validation before tool execution. The timing of the error identifies the failing component.

2. **Examine the PostToolUse payload.** If help-on-error fails, inspect the JSON structure passed from Claude Code. Malformed payloads cause `JSONDecodeError`; missing required fields trigger `KeyError`.

3. **Verify formatter availability.** Format-on-save requires black, ruff, or isort in the environment. Run `which black` or `pip list | grep black` to confirm the dependency exists.

4. **Test security policies manually.** If commands or file access fail unexpectedly, run `validate_bash_command()` or `validate_file_path()` directly with the problematic input. Security violations return `(False, reason)` tuples instead of raising.

5. **Check help template structure.** Freshness check and post-commit hooks expect specific YAML frontmatter in `.help/` files. Missing `generated_at` fields or malformed metadata cause validation failures.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
