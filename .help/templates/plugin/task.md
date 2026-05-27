---
type: task
name: plugin-task
feature: plugin
depth: task
generated_at: 2026-05-27T13:42:27.328414+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Work with the plugin

Use the plugin when you need to extend or modify Claude Code's hooks, slash commands, or MCP configuration — such as changing how session state is discovered, adjusting the compact warning threshold, or customizing the resume prompt.

## Prerequisites

- Access to the project source code under `hooks/`
- Basic familiarity with Python dataclasses and entry-point functions

## Identify the right entry point

The plugin is organized into focused modules. Match your goal to the function that owns it:

| Goal | Function | Module |
|---|---|---|
| Modify the `/handoff` slash command | `main()` | `hooks/_handoff_cli.py` |
| Change the resume prompt format | `build_resume_prompt()` | `hooks/_resume_prompt.py` |
| Change how in-flight specs are discovered | `discover_specs()` | `hooks/_state.py` |
| Change how git state is captured | `git_state()` | `hooks/_state.py` |
| Adjust sentinel file behavior | `session_sentinel_path()` or `prune_stale_sentinels()` | `hooks/_state.py` |
| Change workspace root resolution | `workspace_roots()` | `hooks/_state.py` |
| Adjust context utilization estimation | `estimate_utilization()` | `hooks/_transcript_size.py` |
| Modify the compact warning message | `format_warning()` | `hooks/compact_warning.py` |
| Change security validation logic | `validate_bash_command()` or `validate_file_path()` | `hooks/security_guard.py` |

## Understand the data shapes

Before editing, review the two core dataclasses that flow through most of the plugin:

**`SpecInfo`** — represents one in-flight spec found under a workspace root:
- `slug: str` — identifier for the spec
- `path: Path` — location on disk
- `layer: str`, `phase: str`, `status: str` — workflow position
- `mtime: float` — last modification time

**`GitState`** — snapshot of the worktree at hook-fire time:
- `branch: str` — current branch name
- `last_sha: str`, `last_subject: str` — most recent commit
- `uncommitted: tuple[str, ...]` — list of changed files

## Modify the function

1. Open the module identified in the table above.
2. Read the function's signature, docstring, and return type to confirm it owns the behavior you want to change.
3. Edit the function body. Keep return types consistent — for example, `estimate_utilization()` returns a `float` in `[0.0, 1.0]`, and `validate_bash_command()` returns a `tuple[bool, str]`.
4. If your change affects `build_resume_prompt()`, note that `spec_info` is optional (`SpecInfo | None`) and `workspace_path` defaults to `'~/attune'`.

## Run the tests

Run the plugin-scoped tests to catch regressions before they reach other developers:

```bash
pytest -k "plugin"
```

## Verify success

You know your change works when:

1. `pytest -k "plugin"` passes with no failures.
2. For hook entry points (`main()` functions), manually trigger the hook and confirm the output reflects your change.
3. For `build_resume_prompt()`, inspect the rendered string to confirm the resume body contains the fields from `SpecInfo` and `GitState` that you expect.
4. For `estimate_utilization()`, confirm the returned value stays within `[0.0, 1.0]` for representative transcript inputs.
