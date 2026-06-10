---
type: note
name: plugin-note
feature: plugin
depth: note
generated_at: 2026-06-10T07:07:04.686067+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Note: plugin

## Context

The plugin is a Claude Code extension that wires together skills, hooks, slash commands, and MCP configuration. All hook entry points live under `hooks/` and follow a consistent shape: a public `main()` function that the Claude Code runtime calls directly.

## Public surface

The plugin's shared state layer (`hooks/_state.py`) defines two dataclasses that flow through most of the hook pipeline:

- **`SpecInfo`** — represents one in-flight spec discovered under a workspace root. Fields: `slug`, `path`, `layer`, `phase`, `status`, `mtime`, `effective_status`, `status_source`, and `status_conflict`.
- **`GitState`** — a snapshot of the worktree at hook-fire time. Fields: `branch`, `last_sha`, `last_subject`, and `uncommitted`.

Functions in the same module populate these types:

- `discover_specs(roots)` — walks `specs/` directories under each root and returns a list of `SpecInfo` instances.
- `git_state(cwd)` — returns a `GitState` for the given working directory.
- `workspace_roots(cwd)` — makes a best-effort guess at which roots to scan.
- `session_sentinel_path(session_id)` — returns the path to a per-session compact-warning sentinel file.
- `prune_stale_sentinels(now)` — removes sentinel files older than the TTL.

Other hooks consume these types directly:

- `hooks._resume_prompt.build_resume_prompt(spec_info, git_state, ...)` — renders the user-facing resume prompt from a `SpecInfo` and a `GitState`.
- `hooks.spec_orient.format_orientation(specs)` and `render_spec_pin(spec, char_budget)` — format spec orientation output for display.
- `hooks.compact_warning.format_warning(util, threshold, resume_body)` — composes the compact-warning message from a utilization float produced by `hooks._transcript_size.estimate_utilization(transcript_path)`.
- `hooks.security_guard.validate_bash_command(command)` and `validate_file_path(file_path)` — each return a `(bool, str)` verdict tuple checked before shell operations run.

## Design note

The dataclasses in `hooks/_state.py` act as the shared vocabulary of the hook pipeline. Functions that discover or snapshot state return these types; functions that present or validate state accept them. This keeps discovery logic in one place and lets individual hooks stay focused on a single responsibility.
