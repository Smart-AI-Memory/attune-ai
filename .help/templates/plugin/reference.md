---
feature: plugin
depth: reference
generated_at: 2026-04-06T04:35:37.736926+00:00
source_hash: 671b121fa834def159cbd2cb857178dd617b336c060648c1bb153041e24bab05
status: generated
---

# Plugin reference

Hooks and runtime components that extend Claude Code with automated development workflows.

## Functions

| Function | Description | File |
|----------|-------------|------|
| `main()` | Format Python files automatically after Write or Edit tool use. | `plugin/hooks/format_on_save.py` |
| `main()` | Check if help templates need updates when you start a session. | `plugin/hooks/help_freshness_check.py` |
| `main()` | Suggest relevant help when Bash commands fail. | `plugin/hooks/help_on_error.py` |
| `main()` | Update help templates automatically after git commits. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command()` | Validate Bash commands against security policies before execution. | `plugin/hooks/security_guard.py` |
| `validate_file_path()` | Validate file paths against security policies before access. | `plugin/hooks/security_guard.py` |
| `main()` | Validate tool calls against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Display welcome message when you start Claude Code. | `plugin/hooks/welcome.py` |


## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
