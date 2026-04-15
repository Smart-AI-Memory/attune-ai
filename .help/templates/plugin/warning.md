---
type: warning
feature: plugin
depth: warning
generated_at: 2026-04-14T15:23:04.597228+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin cautions

## What to watch for

Claude Code plugin — skills, hooks, commands, and MCP config.

## Risk areas

### Hook execution order conflicts

Multiple hooks can trigger on the same event. The format_on_save and help_post_commit hooks both run after tool use, potentially interfering with each other's file modifications. If you see unexpected file states or missing help updates, check whether multiple hooks are competing for the same resources.

### Security validation bypasses

The `validate_bash_command()` and `validate_file_path()` functions in security_guard.py return `(True, '')` for allowed operations, but this validation can be circumvented if tools construct commands dynamically or use indirect file access patterns. Commands that build file paths at runtime may bypass the SYSTEM_DIRECTORIES protection.

### Help template staleness

The help_freshness_check and help_post_commit hooks track template updates, but they rely on file timestamps and git state. If you manually edit help files or use git operations that don't trigger hooks, the freshness tracking becomes unreliable, leading to outdated help content being served.

### Stdin dependency in hooks

Several hooks (format_on_save, help_on_error) read from stdin to get tool results. If stdin is empty, redirected, or contains malformed data, these hooks fail silently or produce incorrect behavior. This is particularly problematic when debugging or running tools outside their normal execution context.

## How to avoid problems

1. **Test hook interactions.** Run multiple tools in sequence and verify that each hook's output is preserved. Use `git status` to check for unexpected file modifications after hook execution.

2. **Validate security assumptions.** Don't rely solely on the security guard functions. Test edge cases like symbolic links, relative paths with `..`, and commands that modify their arguments at runtime.

3. **Monitor help freshness manually.** After significant changes, run the help_freshness_check hook directly to verify that template updates are detected correctly.

4. **Provide fallback input.** When testing hooks that read stdin, ensure you have valid input available or the hook can handle empty input gracefully.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
