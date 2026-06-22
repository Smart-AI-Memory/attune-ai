---
type: reference
name: plugin-reference
feature: plugin
depth: reference
generated_at: 2026-06-22T10:00:48.764701+00:00
source_hash: 843f895eed3fa2d3d0b8021830c8c31e3c292c176a967396a76c27deb5a60deb
status: generated
scaffold_hash: 6f4dd2b63d52d539274f6852ceaf44e9ec2a4b35ec27f4d69ffcdcd7d8193d4f
---

# Plugin reference

Claude Code plugin — hooks, session management, and security APIs

Use the `hooks` package to build on or extend the attune-ai Claude Code plugin. The package lets you discover in-flight specs, snapshot git state, gate execution in SDK subprocess sessions, validate shell commands, and compose session-start or resume prompts.

## Classes

| Class | Description |
|-------|-------------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. |
| `GitState` | Snapshot of the worktree's git state at hook fire time. |

Both are dataclasses defined in `plugin/hooks/_state.py`.

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

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `main` | — | `int` | Entry point for the `/handoff` slash command; always returns `0`. | `plugin/hooks/_handoff_cli.py` |
| `build_resume_prompt` | `spec_info: SpecInfo \| None, git_state: GitState, *, workspace_path: str = '~/attune', todo_summary: str \| None = None` | `str` | Render the user-facing resume prompt body. | `plugin/hooks/_resume_prompt.py` |
| `is_sdk_subprocess` | — | `bool` | True when running inside an SDK-spawned `claude` subprocess. | `plugin/hooks/_sdk_gate.py` |
| `exit_if_sdk_subprocess` | — | `None` | Exit 0 with no output when inside an SDK subprocess session. | `plugin/hooks/_sdk_gate.py` |
| `discover_specs` | `roots: list[Path]` | `list[SpecInfo]` | Walk `specs/` directories under each root for in-flight specs. | `plugin/hooks/_state.py` |
| `git_state` | `cwd: Path` | `GitState` | Return branch, last commit, and uncommitted files for `cwd`. | `plugin/hooks/_state.py` |
| `session_sentinel_path` | `session_id: str \| None` | `Path` | Path to the once-per-session compact-warning sentinel. | `plugin/hooks/_state.py` |
| `prune_stale_sentinels` | `now: float \| None = None` | `int` | Delete sentinel files older than the TTL. | `plugin/hooks/_state.py` |
| `workspace_roots` | `cwd: Path \| None = None` | `list[Path]` | Best-effort guess at workspace roots to scan for specs. | `plugin/hooks/_state.py` |
| `estimate_utilization` | `transcript_path: str \| Path` | `float` | Return estimated context utilization in `[0.0, 1.0]`. | `plugin/hooks/_transcript_size.py` |
| `format_warning` | `util: float, threshold: float, resume_body: str` | `str` | Compose the user-facing compact warning and resume prompt. | `plugin/hooks/compact_warning.py` |
| `main` | — | `int` | Entry point for compact warning; never raises. | `plugin/hooks/compact_warning.py` |
| `main` | — | `None` | Read tool result from stdin and format Python files. | `plugin/hooks/format_on_save.py` |
| `main` | — | `None` | Check help template freshness on session start. | `plugin/hooks/help_freshness_check.py` |
| `main` | — | `None` | Read `PostToolUse` payload and suggest help if applicable. | `plugin/hooks/help_on_error.py` |
| `main` | — | `None` | Check for stale help after git commit. | `plugin/hooks/help_post_commit.py` |
| `main` | — | `int` | Surface matching rules once per session; never raises. | `plugin/hooks/jit_recall.py` |
| `main` | — | `int` | Surface top-scoring lessons for this prompt, once per session each. | `plugin/hooks/lesson_recall.py` |
| `main` | — | `int` | Surface the anonymous-usage consent ask once per workspace (MCP / Claude Code). | `plugin/hooks/usage_consent_notice.py` |
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validate a Bash command against security policies. | `plugin/hooks/security_guard.py` |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validate a file path against security policies. | `plugin/hooks/security_guard.py` |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validate a tool call against security policies. | `plugin/hooks/security_guard.py` |
| `main` | — | `int` | Entry point for session recall. | `plugin/hooks/session_recall.py` |
| `main` | — | `int` | Act once per substantive session; never raises. | `plugin/hooks/session_stash.py` |
| `format_orientation` | `specs: list[SpecInfo]` | `str` | Short markdown list of in-flight specs for non-compact starts. | `plugin/hooks/spec_orient.py` |
| `render_spec_pin` | `spec: SpecInfo, char_budget: int = _POST_COMPACT_CHAR_BUDGET` | `str` | Render a spec body for post-compact context restoration. | `plugin/hooks/spec_orient.py` |
| `main` | — | `int` | Branch on `source`; never raises. | `plugin/hooks/spec_orient.py` |
| `main` | — | `None` | Print welcome message to stderr (Claude Code surfaces stderr). | `plugin/hooks/welcome.py` |

## Constants

| Constant | Type | Values | Description |
|----------|------|--------|-------------|
| `__version__` | `str` | `'8.4.0'` | Package version string. |
| `_TERMINAL_VERDICTS` | `frozenset` | `{'closed', 'complete', 'completed', 'retired', 'superseded', 'shipped', 'done'}` | Spec status values that mark a spec as finished. |
| `_ONGOING_VERDICTS` | `frozenset` | `{'living', 'ongoing'}` | Spec status values that mark a spec as actively in progress. |
| `_SPEC_SUBDIRS` | `tuple` | `{'specs', 'docs/specs'}` | Directory names searched for spec files under each workspace root. |
| `_SENTINEL_PREFIX` | `str` | `'.jit-recalled-'` | File prefix for per-session JIT recall sentinels (`hooks/jit_recall`). |
| `_SENTINEL_PREFIX` | `str` | `'.lesson-recalled-'` | File prefix for per-session lesson recall sentinels (`hooks/lesson_recall`). |
| `SYSTEM_DIRECTORIES` | `frozenset` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` | Filesystem paths blocked by the security guard. |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` | Read-only search prefixes that bypass security blocking. |
| `_VALID_TYPES` | `set` | `{'decision', 'pattern', 'bug', 'reference', 'note'}` | Allowed values for a spec's `type` field. |

## Source files

- `plugin/**`

## Tags

`plugin`, `claude-code`
