---
type: warning
name: plugin-warning
feature: plugin
depth: warning
generated_at: 2026-05-27T13:42:27.341658+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Plugin Cautions

## Stale sentinels accumulate silently

`session_sentinel_path(session_id)` writes a file that gates the once-per-session compact warning. If `prune_stale_sentinels()` is never called — or is called with a stale `now` value — old sentinel files persist and suppress warnings that should fire. Call `prune_stale_sentinels()` without arguments so it uses the real wall-clock time, and confirm the return value (number of deleted files) matches your expectations after any test that creates sentinels.

## Context utilization threshold is a float comparison

`estimate_utilization(transcript_path)` returns a value in `[0.0, 1.0]`. `format_warning(util, threshold, resume_body)` compares these two floats directly. If you pass `threshold` as an integer (e.g. `1` instead of `1.0`) or derive it from an environment variable without casting, the comparison silently misbehaves. Always pass `threshold` as a `float`.

## `build_resume_prompt` silently degrades when `spec_info` is `None`

`build_resume_prompt(spec_info, git_state, ...)` accepts `spec_info: SpecInfo | None`. When `spec_info` is `None`, the resume prompt omits spec context — the output is valid but incomplete. This happens whenever `discover_specs(roots)` finds no in-flight specs under the given roots. Before calling `build_resume_prompt`, check whether `discover_specs` returned an empty list and decide whether that is expected for your workspace layout.

## `workspace_roots` may return an empty list

`workspace_roots(cwd)` makes a best-effort guess at roots to scan. If `cwd` is outside a recognized workspace layout, it returns `[]`. Passing an empty list to `discover_specs(roots)` produces no `SpecInfo` results without raising an error, so the absence of specs looks identical to a workspace with no active work. If `discover_specs` returns `[]` unexpectedly, verify that `workspace_roots` is resolving the correct directory.

## `GitState.uncommitted` reflects the worktree at hook-fire time

`git_state(cwd)` captures `uncommitted: tuple[str, ...]` at the moment it is called. If files are staged or modified after `git_state` runs, `GitState.uncommitted` does not update — it is a snapshot, not a live view. Hooks that branch on uncommitted files should call `git_state` as late as possible, immediately before the check.

## `validate_bash_command` and `validate_file_path` return reasons, not exceptions

`validate_bash_command(command)` and `validate_file_path(file_path)` both return `tuple[bool, str]`. A rejected command or path returns `(False, reason)` — no exception is raised. Code that ignores the boolean and only uses the string will silently pass through commands that should have been blocked. Always check the first element of the tuple before proceeding.

## Private helpers in `hooks._state` can change without notice

`hooks._state` is the shared foundation for session-continuity hooks. Its public surface — `discover_specs`, `git_state`, `session_sentinel_path`, `prune_stale_sentinels`, `workspace_roots` — is stable. Any names prefixed with `_` are implementation details that can change between versions without deprecation warnings. Depend only on the documented public functions.
