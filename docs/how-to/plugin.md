---
type: how-to
name: plugin
tags: [plugin, claude-code, hooks, mcp]
source: developer-guidance
---

# How to use the Claude Code plugin

Use this guide when you need to wire up, call, or extend the Claude Code plugin's hooks and commands — session continuity, security validation, spec orientation, and context-utilization warnings.

## Quick start

The following snippet checks context utilization and prints a compact warning when the transcript is getting full:

```python
from hooks._transcript_size import estimate_utilization
from hooks._state import git_state, workspace_roots, discover_specs
from hooks._resume_prompt import build_resume_prompt
from hooks.compact_warning import format_warning
from pathlib import Path

cwd = Path.cwd()
roots = workspace_roots(cwd)
specs = discover_specs(roots)
spec = specs[0] if specs else None

util = estimate_utilization("~/.claude/transcript.jsonl")
if util > 0.8:
    state = git_state(cwd)
    resume = build_resume_prompt(spec, state, workspace_path="~/attune")
    print(format_warning(util, threshold=0.8, resume_body=resume))
```

Running this prints a formatted warning block to stdout when the transcript exceeds 80 % utilization.

## Core API

Each hook module exposes a `main()` entry point callable by Claude Code directly. The shared helpers in `hooks._state` and `hooks._transcript_size` are the building blocks the other hooks rely on.

### State discovery (`hooks._state`)

| Function / Class | Purpose |
|---|---|
| `workspace_roots(cwd)` | Returns candidate workspace root paths to scan for specs |
| `discover_specs(roots)` | Walks `specs/` directories under each root; returns `list[SpecInfo]` |
| `git_state(cwd)` | Snapshots branch, last commit SHA + subject, and uncommitted files |
| `session_sentinel_path(session_id)` | Returns the path of the once-per-session compact-warning sentinel file |
| `prune_stale_sentinels(now)` | Deletes sentinel files older than the TTL; returns count removed |
| `SpecInfo` | Dataclass: `slug`, `path`, `layer`, `phase`, `status`, `mtime` |
| `GitState` | Dataclass: `branch`, `last_sha`, `last_subject`, `uncommitted` |

### Context utilization (`hooks._transcript_size`)

| Function | Purpose |
|---|---|
| `estimate_utilization(transcript_path)` | Returns context utilization as a float in `[0.0, 1.0]` |

### Resume prompt (`hooks._resume_prompt`)

| Function | Purpose |
|---|---|
| `build_resume_prompt(spec_info, git_state, *, workspace_path, todo_summary)` | Renders the user-facing resume prompt body |

### Compact warning (`hooks.compact_warning`)

| Function | Purpose |
|---|---|
| `format_warning(util, threshold, resume_body)` | Composes the full warning message + resume prompt |

### Security (`hooks.security_guard`)

| Function | Purpose |
|---|---|
| `validate_bash_command(command)` | Checks a Bash command against security policies; returns `(allowed, reason)` |
| `validate_file_path(file_path)` | Checks a file path against security policies; returns `(allowed, reason)` |
| `main(context)` | Validates a tool call dict; returns an updated context dict |

### Spec orientation (`hooks.spec_orient`)

| Function | Purpose |
|---|---|
| `format_orientation(specs)` | Returns a short markdown list of in-flight specs for session start |
| `render_spec_pin(spec, char_budget)` | Renders a spec body for post-compact context restoration |

### Hook entry points

| Module | `main()` behavior |
|---|---|
| `hooks._handoff_cli` | CLI wrapper for the `/handoff` slash command |
| `hooks.compact_warning` | Entry point — never raises |
| `hooks.format_on_save` | Reads a tool result from stdin and formats Python files |
| `hooks.help_freshness_check` | Checks help-template freshness on session start |
| `hooks.help_on_error` | Reads a `PostToolUse` payload and suggests help if applicable |
| `hooks.help_post_commit` | Checks for stale help after a git commit |
| `hooks.spec_orient` | Branches on `source`; never raises |
| `hooks.welcome` | Prints a welcome message to stderr (Claude Code surfaces stderr) |

## Integration patterns

### Security guard in a tool-call pipeline

Wrap any outgoing tool call through `hooks.security_guard.main()` before execution. The function accepts the raw context dict Claude Code passes to a `PreToolUse` hook and returns the same dict, potentially with a blocking annotation:

```python
from hooks.security_guard import main as security_check, validate_bash_command

# Quick inline check
allowed, reason = validate_bash_command("rm -rf /private/etc/hosts")
if not allowed:
    raise PermissionError(reason)

# Full hook integration — called by Claude Code automatically,
# but you can invoke it directly in tests:
context = {"tool": "Bash", "input": {"command": "ls -la"}}
result = security_check(context)
```

`SYSTEM_DIRECTORIES` (`{'/etc', '/sys', '/proc', ...}`) and `SEARCH_COMMAND_PREFIXES` are the policy constants the validator checks against.

### Spec orientation at session start

Call `format_orientation` immediately after `discover_specs` to surface in-flight work to the model:

```python
from hooks._state import workspace_roots, discover_specs
from hooks.spec_orient import format_orientation, render_spec_pin
from pathlib import Path

roots = workspace_roots(Path.cwd())
specs = discover_specs(roots)

# Short list for a fresh session
print(format_orientation(specs))

# Detailed pin for post-compact restoration (default 4 000-char budget)
if specs:
    print(render_spec_pin(specs[0]))
```

## See also

- `concepts/task-template-design-patterns.md` — how attune structures help content the plugin surfaces
- `concepts/task-template-migration.md` — background on the session-continuity model the hooks support

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 16 (code fence) | error | `from hooks._transcript_size import …` — module not importable |
| Line 16 (code fence) | error | `from hooks._state import …` — module not importable |
| Line 16 (code fence) | error | `from hooks._resume_prompt import …` — module not importable |
| Line 16 (code fence) | error | `from hooks.compact_warning import …` — module not importable |
| Line 105 (code fence) | error | `from hooks.security_guard import …` — module not importable |
| Line 125 (code fence) | error | `from hooks.spec_orient import …` — module not importable |
