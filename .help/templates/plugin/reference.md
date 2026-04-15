---
type: reference
feature: plugin
depth: reference
generated_at: 2026-04-14T15:22:45.180708+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin reference

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main()` | | `None` | Read tool result from stdin, format Python files |
| `main()` | | `None` | Check help template freshness on session start |
| `main()` | | `None` | Read PostToolUse payload and suggest help if applicable |
| `main()` | | `None` | Check for stale help after git commit |
| `validate_bash_command(command: str)` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies |
| `validate_file_path(file_path: str)` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies |
| `main(context: dict[str, Any])` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies |
| `main()` | | `None` | Print welcome message to stderr (Claude Code surfaces stderr) |

### Return values

#### validate_bash_command
```
(True, '')
```

#### validate_file_path
```
(True, '')
```

#### main (security_guard)
```
'allowed': True
```

## Constants

| Constant | Value |
|----------|-------|
| `__version__` | `'6.0.0'` |
| `SYSTEM_DIRECTORIES` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |

## Module purposes

- **attune-ai core**: Bundled runtime for standalone plugin operation
- **PostToolUse hook**: Auto-format Python files after Write/Edit
- **SessionStart hook**: Check help template freshness
- **PostToolUse hook**: Suggest help when Bash commands fail
- **PostToolUse hook**: Auto-maintain .help/ after git commits
