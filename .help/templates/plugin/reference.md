---
type: reference
name: plugin-reference
feature: plugin
depth: reference
generated_at: 2026-05-27T13:42:27.332532+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Plugin reference

Bundled runtime for standalone plugin operation — skills, hooks, commands, and MCP config.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. | `plugin/hooks/_state.py` |
| `GitState` | Snapshot of the worktree's git state at hook fire time. | `plugin/hooks/_state.py` |

### `SpecInfo` fields

| Field | Type | Default |
|-------|------|---------|
| `slug` | `str` | — |
| `path` | `Path` | — |
| `layer` | `str` | — |
| `phase` | `str` | — |
| `status` | `str` | — |
| `mtime` | `float` | — |

### `GitState` fields

| Field | Type | Default |
|-------|------|---------|
| `branch` | `str` | — |
| `last_sha` | `str` | — |
| `last_subject` | `str` | — |
| `uncommitted` | `tuple[str, ...]` | — |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `main` | — | `int` | CLI entry point for the `/handoff` slash command. | `plugin/hooks/_handoff_cli.py` |
| `build_resume_prompt` | `spec_info: SpecInfo \| None, git_state: GitState, *, workspace_path: str = '~/attune', todo_summary: str \| None = None` | `str` | Render the user-facing resume prompt body. | `plugin/hooks/_resume_prompt.py` |
| `discover_specs` | `roots: list[Path]` | `list[SpecInfo]` | Walk `specs/` directories under each root for in-flight specs. | `plugin/hooks/_state.py` |
| `git_state` | `cwd: Path` | `GitState` | Return branch, last commit, and uncommitted files for `cwd`. | `plugin/hooks/_state.py` |
| `session_sentinel_path` | `session_id: str \| None` | `Path` | Path to the once-per-session compact-warning sentinel. | `plugin/hooks/_state.py` |
| `prune_stale_sentinels` | `now: float \| None = None` | `int` | Delete sentinel files older than the TTL. | `plugin/hooks/_state.py` |
| `workspace_roots` | `cwd: Path \| None = None` | `list[Path]` | Best-effort guess at workspace roots to scan for specs. | `plugin/hooks/_state.py` |
| `estimate_utilization` | `transcript_path: str \| Path` | `float` | Return estimated context utilization in `[0.0, 1.0]`. | `plugin/hooks/_transcript_size.py` |
| `format_warning` | `util: float, threshold: float, resume_body: str` | `str` | Compose the user-facing warning + resume prompt. | `plugin/hooks/compact_warning.py` |
| `main` | — | `int` | Entry point — never raises. | `plugin/hooks/compact_warning.py` |
| `main` | — | `None` | Read tool result from stdin and format Python files. | `plugin/hooks/format_on_save.py` |
| `main` | — | `None` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main` | — | `None` | Read PostToolUse payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main` | — | `None` | Check for stale help after a git commit. | `plugin/hooks/help_post_commit.py` |
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies. | `plugin/hooks/security_guard.py` |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies. | `plugin/hooks/security_guard.py` |
| `format_orientation` | `specs: list[SpecInfo]` | `str` | Short markdown list of in-flight specs for non-compact starts. | `plugin/hooks/spec_orient.py` |
| `render_spec_pin` | `spec: SpecInfo, char_budget: int = _POST_COMPACT_CHAR_BUDGET` | `str` | Render a spec body for post-compact context restoration. | `plugin/hooks/spec_orient.py` |
| `main` | — | `int` | Entry point — branches on `source`, never raises. | `plugin/hooks/spec_orient.py` |
| `main` | — | `None` | Print welcome message to stderr (Claude Code surfaces stderr). | `plugin/hooks/welcome.py` |

## Constants

| Constant | Type | Value |
|----------|------|-------|
| `__version__` | `str` | `'7.2.0'` |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
