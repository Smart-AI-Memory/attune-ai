---
type: warning
feature: plugin
depth: warning
generated_at: 2026-04-19T18:52:56.197470+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Plugin cautions

## What to watch for

Claude Code's plugin system handles automatic formatting, help suggestions, and security validation through hooks and commands. Several common patterns in plugin development can lead to unexpected behavior.

## Risk areas

### Hook execution timing conflicts

The `main()` functions in hook modules run at different lifecycle points and can interfere with each other. For example:

- `format_on_save.py` processes stdin for Python formatting
- `help_on_error.py` reads PostToolUse payloads for error suggestions
- `help_freshness_check.py` runs on session start

If you modify multiple hooks simultaneously, they may compete for the same input streams or environment state.

### Security validation bypass

`validate_bash_command()` and `validate_file_path()` in `security_guard.py` return tuple results that look like boolean checks but contain validation details. Treating them as simple true/false values misses important security context:

```python
# Risky - ignores validation details
is_valid, _ = validate_bash_command(cmd)
if is_valid:
    run_command(cmd)

# Better - handle validation feedback
is_valid, message = validate_bash_command(cmd)
if not is_valid:
    log_security_violation(message)
```

### Version compatibility assumptions

The plugin system uses `__version__ = '6.2.0'` for compatibility checks. Hard-coding version comparisons in custom plugins breaks when the core system updates.

## How to avoid problems

1. **Test hook interactions separately.** Run `pytest -k "hook"` to verify that individual hooks work in isolation before testing combined scenarios.

2. **Handle security validation properly.** Always check both the boolean result and the message from validation functions. Log security rejections for debugging.

3. **Use the public API boundaries.** Stick to documented functions and avoid importing from `plugin.hooks.*` internals directly. The hook registration system is your stable interface.

**Tags:** `plugin`, `claude-code`
