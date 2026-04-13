---
feature: plugin
depth: reference
generated_at: 2026-04-13T17:02:40.480362+00:00
source_hash: 87e746872c84d001921b431b15885746de7e8990a689c551172afc6f72cf1c35
status: generated
---

# Plugin reference

Plugin hooks provide automated assistance and security for Claude Code interactions through a bundled runtime for standalone operation.

## Functions

| Function | Description | File |
|----------|-------------|------|
| `main()` | Automatically formats Python files after Write or Edit tool use. | `plugin/hooks/format_on_save.py` |
| `main()` | Checks help template freshness when a new session starts. | `plugin/hooks/help_freshness_check.py` |
| `main()` | Suggests relevant help when Bash commands fail. | `plugin/hooks/help_on_error.py` |
| `main()` | Maintains .help/ directory freshness after git commits. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command()` | Validates Bash commands against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path()` | Validates file paths against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Validates tool calls against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Displays welcome message through stderr for Claude Code visibility. | `plugin/hooks/welcome.py` |


## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
