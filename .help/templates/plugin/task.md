---
type: task
feature: plugin
depth: task
generated_at: 2026-04-19T18:52:21.386739+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Work with plugin

Use the plugin system when you need to extend Claude Code with automated behaviors, security validation, or help system integration.

## Prerequisites

- Access to the project source code
- Understanding of Claude Code's hook-based architecture
- Familiarity with the `plugin/` directory structure

## Configure plugin behavior

1. **Identify the hook type you need.**
   Claude Code supports several hook types:
   - PostToolUse hooks: Run after tool execution (format, help suggestions)
   - SessionStart hooks: Run when a session begins (freshness checks)
   - Security hooks: Validate commands and file paths before execution

2. **Locate the relevant hook file.**
   Each hook lives in `plugin/hooks/` with a descriptive name:
   - `format_on_save.py` — Auto-formats Python files after Write/Edit tools
   - `help_freshness_check.py` — Checks help template age on session start
   - `help_on_error.py` — Suggests help when Bash commands fail
   - `help_post_commit.py` — Updates help after git commits
   - `security_guard.py` — Validates commands and file paths
   - `welcome.py` — Displays session welcome message

3. **Modify the hook's main function.**
   Each hook file contains a `main()` function that implements its behavior. Read the existing code to understand the current logic, then make targeted changes while preserving the established patterns for error handling and logging.

4. **Test your changes.**
   Run the plugin test suite to verify your modifications don't break existing functionality:
   ```bash
   pytest -k "plugin"
   ```

5. **Verify the hook activates correctly.**
   Trigger the hook's activation condition (save a Python file, start a session, run a failing command, etc.) and confirm your changes work as expected.

## Success criteria

Your plugin modification is complete when:
- The hook executes without errors in its target scenario
- All existing plugin tests pass
- The hook's behavior matches your intended changes
- No unintended side effects occur in other parts of the system
