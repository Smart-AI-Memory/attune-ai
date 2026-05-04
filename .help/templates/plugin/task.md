---
type: task
feature: plugin
depth: task
generated_at: 2026-05-04T02:38:37.974666+00:00
source_hash: b0ee9918b90b55b1b86413bf2ab78f0a590fb78eae098da3ba2886258d9db841
status: generated
---

# Work with plugin

Use the plugin system when you need to modify Claude Code's bundled runtime capabilities, including auto-formatting hooks, help system maintenance, or security validation.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `plugin/`
- Understanding of the specific hook or validation function you need to modify

## Identify the right module

1. **Examine the plugin structure.**
   The plugin directory contains specialized modules:
   - `plugin/hooks/format_on_save.py` — Auto-formats Python files after Write/Edit operations
   - `plugin/hooks/help_freshness_check.py` — Validates help template currency on session start
   - `plugin/hooks/help_on_error.py` — Suggests relevant help when Bash commands fail
   - `plugin/hooks/help_post_commit.py` — Maintains help directory after git commits
   - `plugin/hooks/security_guard.py` — Validates tool calls against security policies
   - `plugin/hooks/welcome.py` — Displays welcome messages to stderr

2. **Read the target function's signature.**
   Each module exposes specific functions with distinct responsibilities:
   - `validate_bash_command(command: str)` — Returns `(True, '')` for allowed commands
   - `validate_file_path(file_path: str)` — Returns `(True, '')` for safe paths
   - `main(context: dict[str, Any])` — Returns `{'allowed': True}` for permitted operations

## Modify the plugin behavior

3. **Locate the specific function.**
   Open the relevant module and find the function that handles your use case. Check its docstring and parameters to confirm it owns the behavior you need to change.

4. **Update the implementation.**
   Modify the function while preserving its return type and error handling patterns. Use the existing constant values like `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES` for consistency.

5. **Test your changes.**
   Run targeted tests to verify your modifications work correctly:
   ```bash
   pytest -k "plugin"
   ```

## Verify the plugin works

Your plugin modification is successful when:
- The specific hook triggers at the expected time (save, session start, command failure, or commit)
- Security validations return the correct boolean and message tuple
- No test failures appear in the plugin test suite
- The plugin integrates seamlessly with Claude Code's existing workflow
