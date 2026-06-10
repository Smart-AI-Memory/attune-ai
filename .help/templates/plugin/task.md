---
type: task
name: plugin-task
feature: plugin
depth: task
generated_at: 2026-06-10T07:07:04.659028+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Work with the plugin hooks

Use the plugin hooks when you need to modify how attune handles session continuity, workspace state discovery, security validation, or any other hook-driven behavior in your Claude Code environment.

## Prerequisites

- Read access to the `hooks/` directory in the plugin source
- A working Python environment with `pytest` available
- Familiarity with which hook fires at which point in the Claude Code lifecycle (see the module list below for entry points)

## Identify the right entry point

Each hook module exposes a `main()` function as its entry point. Match your goal to the module responsible for it:

| Goal | Module | Key function |
|---|---|---|
| Modify the `/handoff` slash command | `hooks/_handoff_cli.py` | `main() -> int` |
| Change the resume prompt shown at session start | `hooks/_resume_prompt.py` | `build_resume_prompt(spec_info, git_state, *, workspace_path, todo_summary)` |
| Change how in-flight specs are discovered | `hooks/_state.py` | `discover_specs(roots)` |
| Change how git state is captured | `hooks/_state.py` | `git_state(cwd)` |
| Adjust workspace root detection | `hooks/_state.py` | `workspace_roots(cwd)` |
| Tune compact-warning sentinel behavior | `hooks/_state.py` | `session_sentinel_path(session_id)`, `prune_stale_sentinels(now)` |
| Change context-utilization estimation | `hooks/_transcript_size.py` | `estimate_utilization(transcript_path)` |
| Change the compact warning message | `hooks/compact_warning.py` | `format_warning(util, threshold, resume_body)` |
| Modify security validation for bash commands or file paths | `hooks/security_guard.py` | `validate_bash_command(command)`, `validate_file_path(file_path)` |
| Modify spec orientation output | `hooks/spec_orient.py` | `format_orientation(specs)`, `render_spec_pin(spec, char_budget)` |

## Modify state discovery

If your change involves how the plugin finds specs or reads workspace state, edit `hooks/_state.py`. The two primary data structures are:

- **`SpecInfo`** — represents one in-flight spec found under a workspace root. Key fields: `slug`, `path`, `layer`, `phase`, `status`, `mtime`, `effective_status`, `status_source`, `status_conflict`.
- **`GitState`** — a snapshot of the worktree at hook-fire time. Fields: `branch`, `last_sha`, `last_subject`, `uncommitted`.

`discover_specs(roots)` walks the `specs/` and `docs/specs/` subdirectories under each root and returns a list of `SpecInfo` objects. `git_state(cwd)` returns a `GitState` for the given working directory.

## Modify the resume prompt

The resume prompt is built entirely inside `build_resume_prompt()` in `hooks/_resume_prompt.py`. It accepts an optional `SpecInfo`, a `GitState`, an optional `workspace_path` (default `~/attune`), and an optional `todo_summary`. Edit this function to change what appears in the prompt body.

## Modify security validation

`hooks/security_guard.py` exposes two validators:

- `validate_bash_command(command) -> tuple[bool, str]` — returns a pass/fail boolean and a reason string.
- `validate_file_path(file_path) -> tuple[bool, str]` — same signature.

The module-level `main(context)` function calls both validators and returns a result dict. Edit the validators to tighten or adjust what commands and paths the plugin allows.

## Run the tests

After making your change, run the hook-specific tests to catch regressions before they affect other developers:

```bash
pytest -k "plugin"
```

## Verify your change

Your change is working correctly when:

1. `pytest -k "plugin"` passes with no failures or errors.
2. The hook entry point you modified (`main()` or the specific function) produces the expected output when triggered manually or through Claude Code.
3. If you changed `discover_specs()` or `workspace_roots()`, confirm the correct `SpecInfo` objects are returned for a known workspace layout.
4. If you changed a validator in `security_guard.py`, confirm that `validate_bash_command()` or `validate_file_path()` returns the expected `(bool, str)` tuple for both allowed and blocked inputs.
