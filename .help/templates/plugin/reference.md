---
type: reference
name: plugin-reference
feature: plugin
depth: reference
generated_at: 2026-05-21T03:20:39.401647+00:00
source_hash: 5586c41f1c99c9715bfc73d5dc9622c7133d156e10d5ec551da7c26153748cf1
status: generated
---

# Plugin reference

Core API for the attune-ai plugin runtime. Provides session continuity, workspace discovery, and Claude Code integration hooks.

## Classes

| Class | Description |
|-------|-------------|
| `SpecInfo` | One in-flight spec discovered under a workspace root |
| `GitState` | Snapshot of the worktree's git state at hook fire time |

### Fields

#### SpecInfo fields

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | Unique identifier for the spec |
| `path` | `Path` | File system location of the spec |
| `layer` | `str` | Spec layer classification |
| `phase` | `str` | Current development phase |
| `status` | `str` | Processing status |
| `mtime` | `float` | Last modification timestamp |

#### GitState fields

| Field | Type | Description |
|-------|------|-------------|
| `branch` | `str` | Current git branch name |
| `last_sha` | `str` | SHA of the most recent commit |
| `last_subject` | `str` | Subject line of the most recent commit |
| `uncommitted` | `tuple[str, ...]` | List of files with uncommitted changes |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | CLI entry point for `/handoff` command |
| `build_resume_prompt` | `spec_info: SpecInfo \| None, git_state: GitState, *, workspace_path: str = '~/attune', todo_summary: str \| None = None` | `str` | Render the user-facing resume prompt body |
| `discover_specs` | `roots: list[Path]` | `list[SpecInfo]` | Walk `specs/` directories under each root for in-flight specs |
| `git_state` | `cwd: Path` | `GitState` | Return branch, last commit, and uncommitted files for `cwd` |
| `session_sentinel_path` | `session_id: str \| None` | `Path` | Path to the once-per-session compact-warning sentinel |
| `prune_stale_sentinels` | `now: float \| None = None` | `int` | Delete sentinel files older than the TTL |
| `workspace_roots` | `cwd: Path \| None = None` | `list[Path]` | Best-effort guess at workspace roots to scan for specs |
| `estimate_utilization` | `transcript_path: str \| Path` | `float` | Return estimated context utilization in `[0.0, 1.0]` |
| `format_warning` | `util: float, threshold: float, resume_body: str` | `str` | Compose the user-facing warning + resume prompt |
| `validate_bash_command` | Command validation parameters | Validation result | Validate a Bash command against security policies |
| `validate_file_path` | Path validation parameters | Validation result | Validate a file path against security policies |
| `format_orientation` | Spec formatting parameters | `str` | Short markdown list of in-flight specs for non-compact starts |
| `render_spec_pin` | Spec rendering parameters | `str` | Render a spec body for post-compact context restoration |

### Return values

#### main function returns

```
0
```

## Constants

| Constant | Type | Values | Description |
|----------|------|--------|-------------|
| `__version__` | `str` | `'7.0.0'` | Plugin version identifier |
| `SYSTEM_DIRECTORIES` | `frozenset` | `'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'` | Protected system directories |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'` | Recognized search command prefixes |
