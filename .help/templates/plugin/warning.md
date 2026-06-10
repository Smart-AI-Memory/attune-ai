---
type: warning
name: plugin-warning
feature: plugin
depth: warning
generated_at: 2026-06-10T07:07:04.674384+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Plugin cautions

## Stale sentinels accumulate if you skip pruning

`session_sentinel_path()` writes a file prefixed with `.jit-recalled-` to mark that a session has already received a compact warning. These sentinel files are not cleaned up automatically — if you call `session_sentinel_path()` without periodically calling `prune_stale_sentinels()`, old sentinels accumulate and can suppress warnings in sessions that should receive them.

**Mitigation:** Call `prune_stale_sentinels()` at a predictable point in your hook lifecycle (for example, at startup or after a session ends). Its return value tells you how many files were removed, which is useful for debugging runaway accumulation.

## `status_conflict` in `SpecInfo` silently overrides `effective_status`

`discover_specs()` populates `SpecInfo` fields including `effective_status` and `status_conflict`. When `status_conflict` is `True`, the `effective_status` field does not simply reflect the `status` header — there is a disagreement between sources. Code that reads `effective_status` without checking `status_conflict` first can act on a resolved value that masks an underlying inconsistency.

**Mitigation:** Always check `spec.status_conflict` before trusting `spec.effective_status` in any logic that gates on spec state (for example, filtering out terminal statuses from `_TERMINAL_VERDICTS`).

## `build_resume_prompt()` silently uses a default workspace path

`build_resume_prompt()` accepts `workspace_path` with a default of `~/attune`. If the actual workspace is elsewhere and you omit this argument, the rendered resume prompt will reference the wrong path — and the error will not surface as an exception; the output will simply be wrong.

**Mitigation:** Always pass `workspace_path` explicitly. Derive it from `workspace_roots()` rather than relying on the default.

## `estimate_utilization()` returns a float in `[0.0, 1.0]`, not a percentage

`estimate_utilization()` returns a value between `0.0` and `1.0`. Passing this directly to `format_warning()` as the `threshold` argument without converting to the same scale as your threshold constant will produce incorrect warning behavior — for example, a threshold of `80` will never be reached by a utilization of `0.95`.

**Mitigation:** Keep your threshold and the return value of `estimate_utilization()` on the same scale. If your threshold is a fraction, express it as a value in `[0.0, 1.0]` as well.

## `git_state()` reflects the working directory at call time

`git_state()` returns a `GitState` snapshot — `branch`, `last_sha`, `last_subject`, and `uncommitted` files — captured at the moment of the call. If you call it once and cache the result across multiple hook operations, the snapshot can go stale: a commit, stash, or branch switch between calls will not be reflected.

**Mitigation:** Call `git_state()` as late as possible in your hook, immediately before you need the data, rather than capturing it at startup.

## Private helpers in `hooks._state` can change without notice

`discover_specs()`, `workspace_roots()`, and `session_sentinel_path()` are public, but several internal behaviors they depend on — including `_SPEC_SUBDIRS`, `_SENTINEL_PREFIX`, and `_TERMINAL_VERDICTS` — are private module-level constants. Code that reaches past the public functions and reads these constants directly will break silently during refactors.

**Mitigation:** Use only the public functions listed in the API. If you need the list of terminal statuses for comparison, derive it from `SpecInfo.effective_status` values returned by `discover_specs()` rather than importing `_TERMINAL_VERDICTS` directly.
