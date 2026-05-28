---
type: note
name: plugin-note
feature: plugin
depth: note
generated_at: 2026-05-27T13:42:27.352453+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Note: plugin

## Context

The plugin integrates attune with Claude Code by wiring together hooks, slash commands, and MCP configuration. All hook logic lives under `hooks/` and is partitioned into focused modules: lifecycle hooks (`format_on_save`, `help_freshness_check`, `help_on_error`, `help_post_commit`, `welcome`), session-continuity utilities (`_handoff_cli`, `_resume_prompt`, `_state`), context-utilization monitoring (`_transcript_size`, `compact_warning`), orientation (`spec_orient`), and a security layer (`security_guard`).

## Shared state model

Two dataclasses in `hooks._state` are the common currency passed between modules:

**`SpecInfo`** represents one in-flight spec discovered under a workspace root:

| Field | Type | Description |
|---|---|---|
| `slug` | `str` | Short identifier for the spec |
| `path` | `Path` | Absolute path to the spec file |
| `layer` | `str` | Architectural layer the spec targets |
| `phase` | `str` | Current lifecycle phase |
| `status` | `str` | Progress status |
| `mtime` | `float` | Last-modified timestamp |

**`GitState`** is a snapshot of the worktree at hook-fire time:

| Field | Type | Description |
|---|---|---|
| `branch` | `str` | Current branch name |
| `last_sha` | `str` | SHA of the most recent commit |
| `last_subject` | `str` | Subject line of the most recent commit |
| `uncommitted` | `tuple[str, ...]` | Paths with uncommitted changes |

`discover_specs(roots)` and `git_state(cwd)` in `hooks._state` are the canonical way to populate these dataclasses. Other modules import and consume them rather than querying git or the filesystem directly.

## Session-continuity flow

When a session ends or context runs long, three functions collaborate to produce a resume prompt:

1. `workspace_roots(cwd)` — resolves the workspace roots to scan.
2. `discover_specs(roots)` — walks `specs/` directories under each root and returns `list[SpecInfo]`.
3. `build_resume_prompt(spec_info, git_state, *, workspace_path, todo_summary)` in `hooks._resume_prompt` — renders the user-facing resume prompt body from a `SpecInfo | None` and a `GitState`.

The `hooks._handoff_cli` module exposes this flow as the `/handoff` slash command via its `main()` entry point.

## Context utilization and compact warning

`estimate_utilization(transcript_path)` in `hooks._transcript_size` returns a float in `[0.0, 1.0]` representing how full the current context window is. When utilization crosses a threshold, `format_warning(util, threshold, resume_body)` in `hooks.compact_warning` composes the visible warning together with the resume prompt. `session_sentinel_path(session_id)` and `prune_stale_sentinels(now)` in `hooks._state` ensure the warning fires at most once per session.

## Security layer

`hooks.security_guard` validates tool calls before execution. `validate_bash_command(command)` blocks commands that target paths in `SYSTEM_DIRECTORIES` (`{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}`) or that use prefixes listed in `SEARCH_COMMAND_PREFIXES`. `validate_file_path(file_path)` applies the same directory check to file operations. Both return `(bool, str)` — a pass/fail flag and an explanation string. The module's `main(context)` entry point wraps these validators for MCP dispatch.
