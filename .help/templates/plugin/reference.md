---
feature: plugin
depth: reference
generated_at: 2026-04-04T02:25:50.650269+00:00
source_hash: 91035b6062c35b9c5a02a46b975ee4d920fbf79b8c3cad1575709d661c5d2cde
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
