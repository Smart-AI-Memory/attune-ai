---
type: error
name: plugin-error
feature: plugin
depth: error
generated_at: 2026-06-10T07:07:04.668091+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Plugin errors

## Common error signatures

Errors in the plugin's hook modules typically fall into three categories:

- **Filesystem errors** (`OSError`, `FileNotFoundError`) — `discover_specs()` walks `specs/` and `docs/specs/` directories under each workspace root. If a root is inaccessible or the path doesn't exist, it raises before returning any `SpecInfo` list. Similarly, `session_sentinel_path()` and `prune_stale_sentinels()` read and delete files under the workspace; permission problems surface here.

- **Git errors** (`subprocess` exceptions, `ValueError`) — `git_state()` shells out to git in the given `cwd`. If `cwd` is not inside a git repository, or git is not on `PATH`, the call fails before populating `GitState.branch`, `GitState.last_sha`, or `GitState.uncommitted`.

- **Validation rejections** (returns `tuple[bool, str]` with `False`) — `validate_bash_command()` and `validate_file_path()` in `hooks.security_guard` do not raise; they return `(False, reason)`. If downstream code treats a falsy result as success, the command or path is silently permitted. Check that callers inspect the first element of the returned tuple.

- **Utilization out-of-range** — `estimate_utilization()` returns a `float` in `[0.0, 1.0]`. A value at or above the threshold passed to `format_warning()` triggers the compact warning prompt. If the transcript path is missing or unreadable, the estimate cannot be computed.

- **Malformed spec metadata** — `SpecInfo.status_conflict` is set to `True` when the `status` field in the spec header disagrees with a derived status. Code that reads `effective_status` without checking `status_conflict` may act on a stale or ambiguous value.

## Where errors originate

Each hook module exposes a `main()` entry point. Failures inside the helpers they call will appear in the traceback under that entry point:

- `hooks._handoff_cli.main()` — orchestrates handoff; depends on `git_state()` and `discover_specs()`.
- `hooks._resume_prompt.build_resume_prompt()` — requires a valid `GitState` and optionally a `SpecInfo`; fails if either is malformed.
- `hooks._state.discover_specs()` — requires readable `specs/` or `docs/specs/` directories under each root returned by `workspace_roots()`.
- `hooks._state.git_state()` — requires a valid git repository at `cwd`.
- `hooks._state.session_sentinel_path()` — constructs the path for a `.jit-recalled-` sentinel file; fails if the session ID produces an invalid path.
- `hooks.security_guard.main()` — returns a result dict; errors inside `validate_bash_command()` or `validate_file_path()` are reflected in that dict rather than raised.
- `hooks.compact_warning.main()` — calls `estimate_utilization()` and `format_warning()`; a missing or unreadable transcript path causes the utilization estimate to fail before the warning is composed.

## How to diagnose

1. **Identify the failing hook.** The traceback's outermost frame will name one of the `main()` entry points above. That tells you which hook fired and which helpers it called.

2. **Check `SpecInfo` fields for conflicts.** If `status_conflict` is `True` on a returned `SpecInfo`, the `status` header disagrees with the derived value. Inspect both `status` and `effective_status` to understand which value the failing code used. Valid terminal statuses are: `closed`, `complete`, `completed`, `retired`, `superseded`, `shipped`, `done`.

3. **Verify workspace roots.** `workspace_roots()` makes a best-effort guess at roots to scan. If `discover_specs()` returns an empty list unexpectedly, confirm that the expected root contains a `specs/` or `docs/specs/` subdirectory and is readable.

4. **Confirm git repository state.** `git_state()` needs a git repo at `cwd`. Run `git status` in that directory to confirm it is a valid worktree. A detached HEAD or a missing repo produces an unusable `GitState`.

5. **Inspect the security guard return value.** Because `validate_bash_command()` and `validate_file_path()` return `(bool, str)` rather than raising, a failure won't produce a traceback. Log or print the full return value of `hooks.security_guard.main()` to see the rejection reason.

6. **Check sentinel files.** Stale `.jit-recalled-` sentinel files can cause `session_recall` or `jit_recall` behavior to appear skipped. Run `prune_stale_sentinels()` manually and confirm it returns a count greater than zero if files were accumulating.

## Source files

- `hooks/_handoff_cli.py`
- `hooks/_resume_prompt.py`
- `hooks/_state.py`
- `hooks/_transcript_size.py`
- `hooks/compact_warning.py`
- `hooks/security_guard.py`

**Tags:** `plugin`, `claude-code`
