---
type: reference
feature: plugin
depth: reference
generated_at: 2026-04-23T03:32:58.968046+00:00
source_hash: 45eadb2e7f205941c8bfaceec972a8cbf3a780ce8b0ca2ce66b2868c4058b340
status: generated
---

# Plugin reference

Hook functions and security policies for Attune's Claude Code integration.

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `main()` | | `None` | Read tool result from stdin, format Python files | `plugin/hooks/format_on_save.py` |
| `main()` | | `None` | Check help template freshness on session start | `plugin/hooks/help_freshness_check.py` |
| `main()` | | `None` | Read PostToolUse payload and suggest help if applicable | `plugin/hooks/help_on_error.py` |
| `main()` | | `None` | Check for stale help after git commit | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command(command: str)` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies | `plugin/hooks/security_guard.py` |
| `validate_file_path(file_path: str)` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies | `plugin/hooks/security_guard.py` |
| `main(context: dict[str, Any])` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies | `plugin/hooks/security_guard.py` |
| `main()` | | `None` | Print welcome message to stderr (Claude Code surfaces stderr) | `plugin/hooks/welcome.py` |

### Return values

#### `validate_bash_command`
```python
(True, '')  # When command passes validation
```

#### `validate_file_path`
```python
(True, '')  # When file path passes validation
```

#### Security guard `main`
```python
{
    'allowed': True  # When tool call passes validation
}
```

## Constants

| Constant | Type | Values | Description |
|----------|------|--------|-------------|
| `__version__` | `str` | `'6.3.0'` | Plugin version |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` | Protected system directories |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` | Allowed search command prefixes |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
