---
type: troubleshooting
feature: plugin
depth: troubleshooting
generated_at: 2026-04-14T15:23:18.648336+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Troubleshoot plugin

## Before you start

Claude Code plugin system provides automated hooks that run during your coding session. These hooks handle Python formatting, help template maintenance, command validation, and error assistance.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Python files not formatting after edits | Run `python -m black --check <file>` to verify Black is installed and working |
| Help suggestions not appearing after command failures | Check if the failing command writes to stderr and exits with non-zero status |
| Security validation blocking valid commands | Test `validate_bash_command("your_command")` directly to see the validation result |
| Welcome message not displaying | Verify stderr output is visible in your environment |

## Step-by-step diagnosis

1. **Reproduce the issue with a single hook.**
   Identify which hook is failing by testing them individually:
   - For format issues: Edit a Python file and save it
   - For help suggestions: Run a command that should fail
   - For security blocks: Try the blocked command in isolation
   - For missing welcome: Start a fresh session

2. **Check hook execution in the logs.**
   Plugin hooks run automatically based on tool events. Enable debug logging to see:
   - When each hook triggers
   - What input data it receives
   - Any errors during processing

3. **Test the core functions directly.**
   Run the hook entry points manually to isolate the problem:
   ```bash
   # Test Python formatting
   echo '{"tool":"Write","file":"test.py"}' | python plugin/hooks/format_on_save.py

   # Test command validation
   python -c "from plugin.hooks.security_guard import validate_bash_command; print(validate_bash_command('ls -la'))"
   ```

4. **Verify dependencies and permissions.**
   Check that required tools are available:
   ```bash
   # For Python formatting
   black --version

   # For git operations
   git --version

   # For file access
   ls -la .help/
   ```

## Common fixes

- **Install missing formatters.** Python formatting requires Black:
  ```bash
  pip install black
  ```

- **Fix file permissions.** Help maintenance needs write access to `.help/`:
  ```bash
  chmod -R u+w .help/
  ```

- **Clear stale git state.** If help post-commit hooks fail:
  ```bash
  git status --porcelain
  git clean -fd  # Remove untracked files if safe
  ```

- **Update security policies.** If legitimate commands are blocked, check that `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES` constants reflect your needs. Note that these are security boundaries and should only be modified carefully.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
