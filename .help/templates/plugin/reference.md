---
feature: plugin
depth: reference
generated_at: 2026-04-04T13:00:34.172497+00:00
source_hash: d77f635d1744204539648a98bb499be7b81f018d08c49a5f270bbf69bc0595a1
status: generated
---

# Plugin Reference

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


## Source Files

- `plugin/**`


## Tags

`plugin`, `claude-code`
