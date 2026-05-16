---
type: troubleshooting
name: cli-troubleshooting
feature: cli
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.821744+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Troubleshoot cli

## Before you start

This page covers the `attune` CLI commands and the `HybridRouter` that maps user input to skill invocations. It includes cost tracking commands (`cmd_costs*`), help browsing (`cmd_help`), memory and lessons commands (`cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_*`), and provider commands.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `attune help` returns no results | Run `attune help-docs --tags` and confirm templates exist for your tag; verify `_CATEGORIES` includes the expected category (`errors`, `warnings`, `tips`, `references`) |
| Cost commands show no data or wrong totals | Confirm cost tracking data exists before resetting — `cmd_costs_reset` clears **all** recorded data (returns `0` on success) |
| `cmd_costs_export` produces an empty or missing file | Check the export path argument in `args`; verify write permissions on the target directory |
| `HybridRouter` routes to the wrong skill | Inspect `~/.attune/preferences` (or the path passed to `--preferences-path`) for a stale `RoutingPreference` entry with a high `usage_count` overriding the correct route |
| `cmd_remember` or `cmd_forget` silently does nothing | Confirm the lessons file path is writable; for `cmd_forget`, verify the line number or keyword matches an existing entry (`cmd_lessons` lists current entries with line numbers) |
| Intermittent routing behavior | Check for environment variables or cached preferences influencing `HybridRouter`; `confidence` and `usage_count` on a `RoutingPreference` record can cause non-obvious routing |
| Rich terminal output is garbled or missing color | This affects the CLI render path (`render_cli()` in `transformers.py`); check that your terminal supports color and that `TERM` or `NO_COLOR` is not overriding Rich's output |

## Diagnosis steps

Work through these in order — each step is cheaper than the next.

1. **Reproduce the failure with a minimal command.**
   Strip the invocation to its required arguments. For example, if `cmd_costs` misbehaves, run it without optional flags first. Confirm the failure occurs before adding complexity.

2. **Check what data is present.**
   Several commands depend on existing state:
   - `cmd_lessons` — lists lessons with line numbers; use this before running `cmd_forget`
   - `cmd_costs` / `cmd_costs_today` — require recorded cost data; if the store was reset, these return empty results by design
   - `cmd_memory_recall` — requires prior `cmd_memory_capture` calls

3. **Inspect routing preferences.**
   If `HybridRouter` routes incorrectly, call `get_suggestions(partial)` with your input prefix to see what the router would suggest. Check the preferences file for entries where `confidence` is high but the mapped `skill` or `args` is stale. Remove or correct the offending record directly in the file.

4. **Enable verbose logging.**
   Re-run with `DEBUG`-level logging to surface the offending state or input:
   ```
   ATTUNE_LOG_LEVEL=DEBUG attune <command>
   ```

5. **Run the CLI test suite.**
   ```
   pytest -k "cli" -v
   ```
   If a test exercises your failing path, its fixtures show you the expected inputs and outputs. A newly failing test after a dependency upgrade points to an environment issue rather than a code bug.

6. **Audit the relevant entry point directly.**
   The commands are defined in `src/attune/cli_commands/`. Open the file for your failing command and trace the early-return paths — most silent failures are an unmet condition returning before the main logic runs.

## Common fixes

- **Stale routing preferences.** If `HybridRouter` consistently routes to the wrong skill, edit or delete the preferences file (default path is passed to `HybridRouter.__init__` as `preferences_path`). You can also call `learn_preference(keyword, skill, args)` to overwrite a bad entry programmatically.

- **Accidentally reset cost data.** `cmd_costs_reset` cannot be undone — it clears all cost tracking records. If you need to preserve data first, run `cmd_costs_export` to write it to a file before resetting:
  ```
  attune costs export --output backup.json
  attune costs reset
  ```

- **Missing lessons entry.** If `cmd_forget` reports nothing to remove, run `cmd_lessons` first to confirm the exact line number or keyword, then retry:
  ```
  attune lessons
  attune forget --line 3
  ```

- **Dependency version mismatch.** A `rich` or `argparse` version change can break terminal rendering or argument parsing. Confirm installed versions match the project's requirements:
  ```
  pip show rich
  ```

- **Wrong template category.** `attune help-docs --tags` only surfaces templates in `_CATEGORIES` (`errors`, `warnings`, `tips`, `references`). If your template is in a different category, it will not appear in filtered results — this is expected behavior, not a bug.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/cost_commands.py`
- `src/attune/cli_commands/help_commands.py`
- `src/attune/cli_commands/` (all command modules)

**Tags:** `cli`, `commands`
