---
type: task
name: plugin-task
feature: plugin
depth: task
generated_at: 2026-06-11T04:47:10.948028+00:00
source_hash: bb1dd6bc42134bdd5537798d5887c1172d0c43bf4a6c4c2dc064f90213e6a7b3
status: generated
scaffold_hash: 50c1caa20aa764e3b2db2159a2560e5480f7bfc5f82efed9516912df86eebf1d
---

# Work with the plugin

Use the plugin when you need to change how attune-ai integrates with Claude Code — including hook behavior, session recall, spec orientation, SDK subprocess gating, or the `/handoff` slash command.

## Prerequisites

- Access to the project source code
- Python environment with `pytest` available

## Identify the right hook

Each module in `hooks/` owns a single responsibility. Match your goal to the correct entry point before you edit anything:

| Goal | Module | Entry point |
|---|---|---|
| Customize the `/handoff` slash command | `hooks/_handoff_cli.py` | `main()` |
| Change the resume-prompt format | `hooks/_resume_prompt.py` | `build_resume_prompt()` |
| Gate a hook from running inside an SDK subprocess | `hooks/_sdk_gate.py` | `exit_if_sdk_subprocess()` |
| Discover in-flight specs under workspace roots | `hooks/_state.py` | `discover_specs()` |
| Snapshot branch, last commit, and dirty files | `hooks/_state.py` | `git_state()` |
| Manage compact-warning sentinels | `hooks/_state.py` | `session_sentinel_path()`, `prune_stale_sentinels()` |
| Estimate context utilization from a transcript | `hooks/_transcript_size.py` | `estimate_utilization()` |
| Validate bash commands or file paths | `hooks/security_guard.py` | `validate_bash_command()`, `validate_file_path()` |
| Orient the session around active specs | `hooks/spec_orient.py` | `main()` |

## Modify the hook

1. **Open the target module.** Read the function's signature, docstring, and return type to confirm it owns the behavior you want to change.

2. **Edit the function.** To change how the resume prompt is structured, edit `build_resume_prompt()` in `hooks/_resume_prompt.py`:

   ```python
   build_resume_prompt(
       spec_info: SpecInfo | None,
       git_state: GitState,
       *,
       workspace_path: str = '~/attune',
       todo_summary: str | None = None,
   ) -> str
   ```

   `SpecInfo` provides `slug`, `path`, `layer`, `phase`, `status`, and `mtime` for each in-flight spec. `GitState` provides `branch`, `last_sha`, `last_subject`, and `uncommitted` files.

3. **Add SDK subprocess gating if needed.** If your hook must not run inside an SDK-spawned `claude` subprocess, call `exit_if_sdk_subprocess()` at the top of `main()`. To check the condition without exiting, call `is_sdk_subprocess()` directly.

4. **Run the tests** to catch regressions:

   ```
   pytest -k "plugin"
   ```

## Verify success

Your change is complete when both of the following are true:

- `pytest -k "plugin"` exits with no failures.
- The hook produces the output you intended when triggered manually or through the normal Claude Code flow.
