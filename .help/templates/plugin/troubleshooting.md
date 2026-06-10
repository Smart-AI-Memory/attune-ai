---
type: troubleshooting
name: plugin-troubleshooting
feature: plugin
depth: troubleshooting
generated_at: 2026-06-10T07:07:04.676749+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Troubleshoot plugin

## Before you start

These steps cover the attune plugin's hooks, slash commands, and MCP configuration — including session continuity hooks, security guards, spec discovery, and transcript monitoring.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `/attune` or other skill commands show no matches | Run `claude plugin list` and confirm `attune-ai` appears |
| Skills appear but produce no output | Run `claude plugin marketplace list` and verify the marketplace was added |
| Two conflicting skill triggers fire | Run `claude plugin list` and check for both `attune-lite` and `attune-ai` — only one should be installed |
| `session_recall` or `session_stash` produces unexpected results | Check for stale sentinel files: call `prune_stale_sentinels()` and inspect the path returned by `session_sentinel_path(session_id)` |
| `spec_orient` shows no specs or wrong specs | Confirm `workspace_roots()` returns the expected paths, then verify `discover_specs(roots)` finds `.yaml` files under `specs/` or `docs/specs/` subdirectories |
| Compact warning fires every session instead of once | A sentinel file under the prefix `.jit-recalled-` may be missing or stale — call `prune_stale_sentinels()` to clean up |
| `security_guard` blocks a command you expect to allow | Pass the command string to `validate_bash_command(command)` and inspect the returned `(bool, str)` reason |
| Context utilization reading seems wrong | Call `estimate_utilization(transcript_path)` directly and confirm the returned float is in `[0.0, 1.0]` |
| `spec_orient` reports a status conflict | Check the `SpecInfo` fields `status_conflict` and `status_source` on the affected spec |

## Step-by-step diagnosis

1. **Reproduce the failure in isolation.**
   Confirm the failure occurs outside its normal trigger context. For hook entry points, call `main()` directly from a shell or a one-line Python script with the minimal required environment.

2. **Check plugin installation.**
   Run `claude plugin list` to confirm `attune-ai` is installed and no conflicting plugin (such as `attune-lite`) is also present. If the plugin is missing, reinstall it:
   ```
   claude plugin marketplace add Smart-AI-Memory/attune-ai
   claude plugin install attune-ai@attune-ai
   ```

3. **Inspect workspace and spec discovery.**
   Call `workspace_roots()` to confirm it returns your expected project root, then pass those roots to `discover_specs(roots)` to verify it returns the `SpecInfo` objects you expect. Check the `slug`, `path`, `layer`, `phase`, `status`, and `effective_status` fields on each result.

4. **Check git state.**
   Call `git_state(cwd)` with your working directory. Confirm that `branch`, `last_sha`, `last_subject`, and `uncommitted` reflect the actual repository state. A wrong `cwd` is a common cause of stale or empty `GitState` values.

5. **Audit sentinel files.**
   Call `session_sentinel_path(session_id)` to find the expected sentinel path, then call `prune_stale_sentinels()` to remove any files older than the TTL. Re-run the failing hook after pruning.

6. **Check the security guard.**
   If `security_guard` is blocking or allowing something unexpectedly, call `validate_bash_command(command)` or `validate_file_path(file_path)` directly. Each returns a `(bool, str)` tuple — the string explains the verdict. Paths under `SYSTEM_DIRECTORIES` (`/etc`, `/sys`, `/proc`, and others) are always blocked.

7. **Check transcript utilization.**
   If `compact_warning` behaves unexpectedly, call `estimate_utilization(transcript_path)` and compare the result against the threshold passed to `format_warning(util, threshold, resume_body)`. Confirm the transcript path is correct and the file is not empty.

8. **Run the related tests.**
   Run `pytest -k "plugin" -v` to confirm which paths are covered. A failing test that exercises your symptom narrows the search immediately.

## Common fixes

- **Conflicting plugins.** Remove the duplicate before reinstalling:
  ```
  claude plugin uninstall attune-lite
  claude plugin install attune-ai@attune-ai
  ```

- **Missing marketplace source.** If `claude plugin list` shows nothing, add the marketplace first:
  ```
  claude plugin marketplace add Smart-AI-Memory/attune-ai
  claude plugin install attune-ai@attune-ai
  ```

- **Stale sentinels causing repeated compact warnings.** Call `prune_stale_sentinels()` from Python or add a one-time invocation to your session setup. The function returns the count of deleted files.

- **Wrong workspace root.** If `discover_specs()` returns an empty list, `workspace_roots()` may be resolving to the wrong directory. Pass an explicit `cwd` argument to override the default (`~/attune`).

- **`SpecInfo` status conflict.** When `status_conflict` is `True`, the spec's `status_source` field indicates whether the status came from its header or another source. Resolve the conflict by editing the spec file directly so the header status matches the intended `effective_status`.

- **Dependency or environment drift.** If a hook worked previously without a code change, confirm your Python environment is clean. Run `pip show` on any recently updated packages and verify the installed versions match what the plugin was last tested against.

## Source files

- `hooks/_handoff_cli.py`
- `hooks/_resume_prompt.py`
- `hooks/_state.py`
- `hooks/_transcript_size.py`
- `hooks/compact_warning.py`
- `hooks/security_guard.py`
- `hooks/session_recall.py`
- `hooks/session_stash.py`
- `hooks/spec_orient.py`

**Tags:** `plugin`, `claude-code`
