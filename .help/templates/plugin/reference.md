---
type: reference
feature: plugin
depth: reference
generated_at: 2026-04-19T18:52:32.517466+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Plugin reference

Hook functions and security validation for Claude Code integration.

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `main()` | | `None` | Read tool result from stdin, format Python files. | `plugin/hooks/format_on_save.py` |
| `main()` | | `None` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main()` | | `None` | Read PostToolUse payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main()` | | `None` | Check for stale help after git commit. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command(command: str)` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path(file_path: str)` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies. | `plugin/hooks/security_guard.py` |
| `main(context: dict[str, Any])` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | | `None` | Print welcome message to stderr (Claude Code surfaces stderr). | `plugin/hooks/welcome.py` |

## Return values

### validate_bash_command

Returns validation status and error message:

```python
(True, '')
```

### validate_file_path

Returns validation status and error message:

```python
(True, '')
```

### main (security_guard)

Returns validation result:

```python
{'allowed': True}
```

## Constants

| Constant | Type | Description |
|----------|------|-------------|
| `__version__` | `str` | Plugin version: `'6.2.0'` |
| `SYSTEM_DIRECTORIES` | `frozenset` | Protected directories: `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | Allowed search commands: `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
