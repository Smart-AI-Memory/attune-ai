---
feature: plugin
depth: reference
generated_at: 2026-04-13T18:07:44.288588+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin reference


## Functions

| Function | Description | File |
|----------|-------------|------|
| `main()` | Read tool result from stdin, format Python files. | `plugin/hooks/format_on_save.py` |
| `main()` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main()` | Read PostToolUse payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main()` | Check for stale help after git commit. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command()` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path()` | Validate a file path against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Validate a tool call against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Print welcome message to stderr (Claude Code surfaces stderr). | `plugin/hooks/welcome.py` |


## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
