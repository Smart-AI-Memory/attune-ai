---
type: reference
feature: plugin
depth: reference
generated_at: 2026-05-04T02:38:49.851215+00:00
source_hash: b0ee9918b90b55b1b86413bf2ab78f0a590fb78eae098da3ba2886258d9db841
status: generated
---

# Plugin reference

Runtime hooks and security policies for Claude Code integration.

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | | `None` | Read tool result from stdin, format Python files |
| `main` | | `None` | Check help template freshness on session start |
| `main` | | `None` | Read PostToolUse payload and suggest help if applicable |
| `main` | | `None` | Check for stale help after git commit |
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies |
| `main` | | `None` | Print welcome message to stderr (Claude Code surfaces stderr) |

### validate_bash_command returns

```
(True, '')
```

### validate_file_path returns

```
(True, '')
```

### main (security_guard) returns

```
{
    'allowed': True
}
```

## Constants

| Constant | Type | Values |
|----------|------|---------|
| `__version__` | `str` | `'6.3.0'` |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
