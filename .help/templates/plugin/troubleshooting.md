---
type: troubleshooting
feature: plugin
depth: troubleshooting
generated_at: 2026-04-19T18:53:08.555113+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Troubleshoot Claude Code plugin issues

## Before you start

The Claude Code plugin provides skills, hooks, commands, and MCP configuration for attune-ai functionality.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Plugin skills not available (no `/attune` commands) | Run `claude plugin list` to verify installation |
| Python files not formatting after tool use | Check `format_on_save.py` hook registration and tool result input |
| Help suggestions missing after command failures | Verify `help_on_error.py` hook receives PostToolUse payload |
| Security validation blocking valid commands | Test with `validate_bash_command()` and `validate_file_path()` directly |
| Welcome message not appearing | Confirm stderr output is visible in Claude Code interface |

## Step-by-step diagnosis

1. **Verify plugin installation**
   Check if the plugin is properly installed and activated:
   ```bash
   claude plugin list
   claude plugin marketplace list
   ```

2. **Test hook functionality**
   Reproduce the issue with minimal input. For formatting issues, try a simple Python tool use. For help suggestions, trigger a command failure.

3. **Enable debug logging**
   Increase log verbosity to see detailed plugin execution:
   ```bash
   export CLAUDE_LOG_LEVEL=DEBUG
   ```

4. **Check specific entry points**
   Test the relevant main functions based on your symptom:
   - Format issues: `main()` in `format_on_save.py`
   - Session problems: `main()` in `help_freshness_check.py`
   - Missing help: `main()` in `help_on_error.py`
   - Git workflow: `main()` in `help_post_commit.py`
   - Security blocks: `validate_bash_command()` or `validate_file_path()` in `security_guard.py`

5. **Run plugin tests**
   Execute the test suite to identify failing components:
   ```bash
   pytest -k "plugin" -v
   ```

## Common fixes

- **Reinstall plugin**: Remove and reinstall if skills are missing:
  ```bash
  claude plugin uninstall attune-ai
  claude plugin marketplace add Smart-AI-Memory/attune-ai
  claude plugin install attune-ai@attune-ai
  ```

- **Remove conflicting plugins**: Only install one attune plugin (attune-lite or attune-ai, not both)

- **Reset environment variables**: Clear stale environment state that may affect plugin behavior

- **Update dependencies**: Version mismatches can break functionality:
  ```bash
  pip show claude-plugin-sdk
  ```

- **Check file permissions**: Ensure the plugin can read/write necessary files and directories

## Source files

- `plugin/hooks/format_on_save.py` — PostToolUse hook for Python formatting
- `plugin/hooks/help_freshness_check.py` — SessionStart hook for help template checks
- `plugin/hooks/help_on_error.py` — PostToolUse hook for command failure suggestions
- `plugin/hooks/help_post_commit.py` — PostToolUse hook for git commit help maintenance
- `plugin/hooks/security_guard.py` — Tool call validation against security policies
- `plugin/hooks/welcome_message.py` — Session welcome message display

**Tags:** `plugin`, `claude-code`
