---
type: troubleshooting
name: plugin-troubleshooting
feature: plugin
depth: troubleshooting
generated_at: 2026-05-27T13:42:27.343719+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Troubleshoot plugin

The attune plugin bundles skills, hooks, commands, and MCP config for Claude Code. Use this guide when a hook misbehaves, a slash command produces unexpected output, or the plugin silently does nothing.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `/attune` or other skill commands show no matches | Run `claude plugin list` and confirm `attune-ai` appears. If not, see **Fix: plugin not installed** below. |
| Hook fires but produces wrong output | Confirm the correct entry point ran — each hook module exposes its own `main()`. Check that `SpecInfo` fields (`slug`, `phase`, `status`) match what the hook expects. |
| Hook fires but produces no output | Check whether an early return is swallowing the result. For `spec_orient`, verify that `discover_specs()` found at least one `SpecInfo` under your workspace roots. |
| Compact warning never appears | Run `estimate_utilization()` against your transcript path and confirm the returned float exceeds the configured threshold. Also check whether a sentinel file from a previous session is suppressing the warning — call `prune_stale_sentinels()` to clear stale ones. |
| Resume prompt is empty or malformed | Confirm `build_resume_prompt()` receives a valid `GitState` (non-empty `branch`, `last_sha`). If `spec_info` is `None`, the prompt renders without spec context — check that `discover_specs()` returns results for your workspace roots. |
| Security guard blocks a legitimate command | Call `validate_bash_command()` or `validate_file_path()` directly against the string being rejected and inspect the returned reason string. Check whether the command prefix is in `SEARCH_COMMAND_PREFIXES` or the path is under `SYSTEM_DIRECTORIES`. |
| Two attune plugins installed simultaneously | Run `claude plugin list` and confirm only one of `attune-lite` or `attune-ai` is present. Duplicate installs cause conflicting skill triggers. |

## Diagnosis steps

1. **Reproduce with the minimal call.**
   Before enabling any logging, confirm you can reproduce the failure by calling the relevant entry point directly. Each hook module exposes a `main()` function — run it in isolation and note whether the failure persists without the surrounding Claude Code context.

2. **Check workspace discovery.**
   Many hooks depend on `workspace_roots()` returning the correct paths. Call it from your working directory and verify the output. If it returns an empty list, `discover_specs()` will find no specs and hooks that depend on `SpecInfo` will silently short-circuit.

3. **Inspect git state.**
   If the resume prompt or handoff output looks wrong, call `git_state(cwd)` against your repo and print the resulting `GitState`. Confirm `branch`, `last_sha`, `last_subject`, and `uncommitted` all reflect the current worktree.

4. **Check transcript utilization.**
   If the compact warning is misfiring or never appears, call `estimate_utilization(transcript_path)` and compare the returned float (range `0.0`–`1.0`) against your configured threshold.

5. **Check sentinel state.**
   If a hook that should fire once per session is not firing, a stale sentinel file may be suppressing it. Call `prune_stale_sentinels()` — it returns the number of files it deleted. If it deletes one, the sentinel was the cause.

6. **Run the related tests.**
   `pytest -k "plugin" -v` shows which paths have coverage. A failing test that exercises your symptom confirms the regression and gives you a fixture to work from.

## Common fixes

**Plugin not installed or not found**
```
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```
If skills still don't appear, remove any conflicting plugin first: `claude plugin list` → remove the duplicate → reinstall.

**Conflicting duplicate plugins**
Only one of `attune-lite` or `attune-ai` should be installed. Remove the other:
```
claude plugin remove attune-lite
```

**`discover_specs()` returns an empty list**
Verify your `specs/` directory exists under at least one of the paths returned by `workspace_roots()`. The function walks `specs/` subdirectories under each root — if the directory is missing or misnamed, it returns nothing.

**Stale sentinel suppressing a hook**
```python
from hooks._state import prune_stale_sentinels
removed = prune_stale_sentinels()
print(f"Removed {removed} stale sentinel(s)")
```

**Security guard false positive**
`validate_bash_command()` blocks any command whose prefix does not appear in `SEARCH_COMMAND_PREFIXES` and whose behavior looks destructive. If a legitimate command is blocked, inspect the second element of the returned tuple for the rejection reason, then adjust the command string to match an allowed prefix or raise the issue for a policy update — changing `SEARCH_COMMAND_PREFIXES` or `SYSTEM_DIRECTORIES` requires a change to `hooks.security_guard`.

**Version mismatch after a dependency upgrade**
```
pip show attune-ai
```
Confirm the installed version matches what your workspace expects. A version mismatch in the plugin bundle can change hook behavior without any local code change.

## Source files

- `hooks/_handoff_cli.py`
- `hooks/_resume_prompt.py`
- `hooks/_state.py`
- `hooks/_transcript_size.py`
- `hooks/compact_warning.py`
- `hooks/format_on_save.py`
- `hooks/security_guard.py`
- `hooks/spec_orient.py`

**Tags:** `plugin`, `claude-code`, `setup`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 66 (code fence) | error | `from hooks._state import …` — module not importable |
