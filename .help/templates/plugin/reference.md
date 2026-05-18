---
feature: plugin
depth: reference
generated_at: 2026-05-17T18:27:08.915959+00:00
source_hash: 7c317f125965385a2a8e8ed6605ef6bd454625bc8fded43149d47d64438b73b0
status: generated
---

# Plugin reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. | `plugin/hooks/_state.py` |
| `GitState` | Snapshot of the worktree's git state at hook fire time. | `plugin/hooks/_state.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `main()` | — | `plugin/hooks/_handoff_cli.py` |
| `build_resume_prompt()` | Render the user-facing resume prompt body. | `plugin/hooks/_resume_prompt.py` |
| `discover_specs()` | Walk ``specs/`` directories under each root for in-flight specs. | `plugin/hooks/_state.py` |
| `git_state()` | Return branch, last commit, and uncommitted files for ``cwd``. | `plugin/hooks/_state.py` |
| `session_sentinel_path()` | Path to the once-per-session compact-warning sentinel. | `plugin/hooks/_state.py` |
| `prune_stale_sentinels()` | Delete sentinel files older than the TTL. | `plugin/hooks/_state.py` |
| `workspace_roots()` | Best-effort guess at workspace roots to scan for specs. | `plugin/hooks/_state.py` |
| `estimate_utilization()` | Return estimated context utilization in ``[0.0, 1.0]``. | `plugin/hooks/_transcript_size.py` |
| `format_warning()` | Compose the user-facing warning + resume prompt. | `plugin/hooks/compact_warning.py` |
| `main()` | Entry point — never raises. | `plugin/hooks/compact_warning.py` |
| `main()` | Read tool result from stdin, format Python files. | `plugin/hooks/format_on_save.py` |
| `main()` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main()` | Read PostToolUse payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main()` | Check for stale help after git commit. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command()` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path()` | Validate a file path against security policies. | `plugin/hooks/security_guard.py` |
| `main()` | Validate a tool call against security policies. | `plugin/hooks/security_guard.py` |
| `format_orientation()` | Short markdown list of in-flight specs for non-compact starts. | `plugin/hooks/spec_orient.py` |
| `render_spec_pin()` | Render a spec body for post-compact context restoration. | `plugin/hooks/spec_orient.py` |
| `main()` | Entry point — branches on ``source``, never raises. | `plugin/hooks/spec_orient.py` |
| `main()` | Print welcome message to stderr (Claude Code surfaces stderr). | `plugin/hooks/welcome.py` |


## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
