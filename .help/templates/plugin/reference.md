---
type: reference
name: plugin-reference
feature: plugin
depth: reference
generated_at: 2026-06-11T04:47:10.950871+00:00
source_hash: bb1dd6bc42134bdd5537798d5887c1172d0c43bf4a6c4c2dc064f90213e6a7b3
status: generated
scaffold_hash: 7d28fde9c63be053e410fbb26d3b2da226e16e2ab69de2f5d5acd275801fc037
---

# Plugin reference

Use this API to manage workspace state, validate shell commands, build session-resume prompts, and hook into Claude Code lifecycle events. Plugin version: `8.3.0`.

## Classes

| Class | Description | Module |
|-------|-------------|--------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. | `hooks._state` |
| `GitState` | Snapshot of the worktree's git state at hook fire time. | `hooks._state` |

### `SpecInfo` fields

| Field | Type | Default |
|-------|------|---------|
| `slug` | `str` | — |
| `path` | `Path` | — |
| `layer` | `str` | — |
| `phase` | `str` | — |
| `status` | `str` | — |
| `mtime` | `float` | — |
| `effective_status` | `str` | `''` |
| `status_source` | `str` | `'header'` |
| `status_conflict` | `bool` | `False` |

### `GitState` fields

| Field | Type | Default |
|-------|------|---------|
| `branch` | `str` | — |
| `last_sha` | `str` | — |
| `last_subject` | `str` | — |
| `uncommitted` | `tuple[str, ...]` | — |

## Functions

Functions are grouped by module.

### `hooks._state`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `discover_specs` | `roots: list[Path]` | `list[SpecInfo]` | Walk `specs/` directories under each root for in-flight specs. |
| `git_state` | `cwd: Path` | `GitState` | Return branch, last commit, and uncommitted files for `cwd`. |
| `session_sentinel_path` | `session_id: str | None` | `Path` | Path to the once-per-session compact-warning sentinel. |
| `prune_stale_sentinels` | `now: float | None = None` | `int` | Delete sentinel files older than the TTL. |
| `workspace_roots` | `cwd: Path | None = None` | `list[Path]` | Best-effort guess at workspace roots to scan for specs. |

### `hooks._resume_prompt`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `build_resume_prompt` | `spec_info: SpecInfo | None, git_state: GitState, *, workspace_path: str = '~/attune', todo_summary: str | None = None` | `str` | Render the user-facing resume prompt body. |

### `hooks._sdk_gate`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_sdk_subprocess` | — | `bool` | True when running inside an SDK-spawned `claude` subprocess. |
| `exit_if_sdk_subprocess` | — | `None` | Exit 0 with no output when inside an SDK subprocess session. |

### `hooks._transcript_size`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `estimate_utilization` | `transcript_path: str | Path` | `float` | Return estimated context utilization in `[0.0, 1.0]`. |

### `hooks._handoff_cli`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Entry point for the `/handoff` slash command. Always returns `0`. |

### `hooks.compact_warning`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_warning` | `util: float, threshold: float, resume_body: str` | `str` | Compose the user-facing compact warning and resume prompt. |
| `main` | — | `int` | Entry point — never raises. |

### `hooks.format_on_save`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Read tool result from stdin and format Python files. |

### `hooks.help_freshness_check`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Check help template freshness on session start. |

### `hooks.help_on_error`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Read PostToolUse payload and suggest help if applicable. |

### `hooks.help_post_commit`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Check for stale help after git commit. |

### `hooks.jit_recall`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Entry point — surface matching rules once per session, never raises. |

### `hooks.security_guard`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies. |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies. |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies. |

### `hooks.session_recall`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | — |

### `hooks.session_stash`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Entry point — acts once per substantive session, never raises. |

### `hooks.spec_orient`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_orientation` | `specs: list[SpecInfo]` | `str` | Short markdown list of in-flight specs for non-compact starts. |
| `render_spec_pin` | `spec: SpecInfo, char_budget: int = _POST_COMPACT_CHAR_BUDGET` | `str` | Render a spec body for post-compact context restoration. |
| `main` | — | `int` | Entry point — branches on `source`, never raises. |

### `hooks.welcome`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Print welcome message to stderr (Claude Code surfaces stderr). |

## Constants

| Constant | Type | Value |
|----------|------|-------|
| `__version__` | `str` | `'8.3.0'` |
| `_TERMINAL_VERDICTS` | `frozenset` | `{'closed', 'complete', 'completed', 'retired', 'superseded', 'shipped', 'done'}` |
| `_ONGOING_VERDICTS` | `frozenset` | `{'living', 'ongoing'}` |
| `_SPEC_SUBDIRS` | `tuple` | `{'specs', 'docs/specs'}` |
| `_SENTINEL_PREFIX` | `str` | `'.jit-recalled-'` |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` |
| `_VALID_TYPES` | `set` | `{'decision', 'pattern', 'bug', 'reference', 'note'}` |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
