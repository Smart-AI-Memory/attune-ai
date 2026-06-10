---
type: reference
name: plugin-reference
feature: plugin
depth: reference
generated_at: 2026-06-10T07:07:04.663701+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Plugin reference

Claude Code plugin — skills, hooks, commands, and MCP config

## Classes

`SpecInfo` and `GitState` are defined in `plugin/hooks/_state.py` and passed throughout the session-continuity hooks.

| Class | Description |
|-------|-------------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. |
| `GitState` | Snapshot of the worktree's git state at hook fire time. |

### `SpecInfo` fields

| Field | Type | Default |
|-------|------|---------|
| `slug` | `str` | |
| `path` | `Path` | |
| `layer` | `str` | |
| `phase` | `str` | |
| `status` | `str` | |
| `mtime` | `float` | |
| `effective_status` | `str` | `''` |
| `status_source` | `str` | `'header'` |
| `status_conflict` | `bool` | `False` |

### `GitState` fields

| Field | Type | Default |
|-------|------|---------|
| `branch` | `str` | |
| `last_sha` | `str` | |
| `last_subject` | `str` | |
| `uncommitted` | `tuple[str, ...]` | |

## Functions

### `plugin/hooks/_handoff_cli.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Entry point for the `/handoff` slash command. |

### `plugin/hooks/_resume_prompt.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `build_resume_prompt` | `spec_info: SpecInfo \| None, git_state: GitState, *, workspace_path: str = '~/attune', todo_summary: str \| None = None` | `str` | Render the user-facing resume prompt body. |

### `plugin/hooks/_state.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `discover_specs` | `roots: list[Path]` | `list[SpecInfo]` | Walk `specs/` directories under each root for in-flight specs. |
| `git_state` | `cwd: Path` | `GitState` | Return branch, last commit, and uncommitted files for `cwd`. |
| `session_sentinel_path` | `session_id: str \| None` | `Path` | Path to the once-per-session compact-warning sentinel. |
| `prune_stale_sentinels` | `now: float \| None = None` | `int` | Delete sentinel files older than the TTL. |
| `workspace_roots` | `cwd: Path \| None = None` | `list[Path]` | Best-effort guess at workspace roots to scan for specs. |

### `plugin/hooks/_transcript_size.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `estimate_utilization` | `transcript_path: str \| Path` | `float` | Return estimated context utilization in `[0.0, 1.0]`. |

### `plugin/hooks/compact_warning.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_warning` | `util: float, threshold: float, resume_body: str` | `str` | Compose the user-facing warning and resume prompt. |
| `main` | — | `int` | Entry point — never raises. |

### `plugin/hooks/format_on_save.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Read tool result from stdin and format Python files. |

### `plugin/hooks/help_freshness_check.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Check help template freshness on session start. |

### `plugin/hooks/help_on_error.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Read PostToolUse payload and suggest help if applicable. |

### `plugin/hooks/help_post_commit.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Check for stale help after a git commit. |

### `plugin/hooks/jit_recall.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Surface matching rules once per session — never raises. |

### `plugin/hooks/security_guard.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies. |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies. |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies. |

### `plugin/hooks/session_recall.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Entry point for session recall. |

### `plugin/hooks/session_stash.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Acts once per substantive session — never raises. |

### `plugin/hooks/spec_orient.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_orientation` | `specs: list[SpecInfo]` | `str` | Short markdown list of in-flight specs for non-compact starts. |
| `render_spec_pin` | `spec: SpecInfo, char_budget: int = _POST_COMPACT_CHAR_BUDGET` | `str` | Render a spec body for post-compact context restoration. |
| `main` | — | `int` | Branches on `source` — never raises. |

### `plugin/hooks/welcome.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Print the welcome message to stderr (Claude Code surfaces stderr). |

## Constants

| Constant | Type | Value |
|----------|------|-------|
| `__version__` | `str` | `'8.1.0'` |
| `_TERMINAL_VERDICTS` | `frozenset` | `{'closed', 'complete', 'completed', 'retired', 'superseded', 'shipped', 'done'}` |
| `_ONGOING_VERDICTS` | `frozenset` | `{'living', 'ongoing'}` |
| `_SPEC_SUBDIRS` | `tuple` | `{'specs', 'docs/specs'}` |
| `_SENTINEL_PREFIX` | `str` | `'.jit-recalled-'` |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |
| `_VALID_TYPES` | `set` | `{'decision', 'pattern', 'bug', 'reference', 'note'}` |

## Tags

`plugin`, `claude-code`
