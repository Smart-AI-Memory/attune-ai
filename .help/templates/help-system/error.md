---
type: error
name: help-system-error
feature: help-system
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Help System errors

## Common error signatures

Errors in the help system fall into three main categories:

- **`ValueError: Invalid feature name: {...}`** — raised by `generate_feature_templates()` when the `Feature` passed has a name that fails validation. Check the `feature.name` field before calling the generator.
- **`FileNotFoundError` / `OSError`** — raised by `load_manifest()`, `save_manifest()`, `check_staleness()`, or `run_maintenance()` when `help_dir` or `project_root` does not exist or is not readable. Verify both paths before calling these functions.
- **`KeyError` / `None` return from `populate()` or `populate_progressive()`** — `populate()` returns `None` when the `template_id` does not resolve to a file under `generated_dir`. A missing or incorrect `generated_dir` is the most common cause.
- **Stale hash mismatch** — `check_staleness()` returns a `StalenessReport` with `stale_count > 0` when source files have changed since the last `run_maintenance()` run. This is not an exception, but it causes `get_workflow_help()` and `get_precursor_warnings()` to serve outdated templates.

## Where errors originate

The following functions are the most common raise sites. The cause and the likely fix are paired for each:

- **`generate_feature_templates(feature, help_dir, project_root)`** — raises `ValueError` for an invalid `feature.name`. Ensure the `Feature` dataclass was constructed with a non-empty, valid name string.
- **`load_manifest(help_dir)` / `save_manifest(manifest, help_dir)`** — raises `OSError` if `help_dir` does not exist or the process lacks write permission. Create the directory and check permissions before calling either function.
- **`scan_project(project_root)`** — raises `OSError` if `project_root` is not a readable directory. Returns an empty list (no exception) when no features are detected, which causes `proposals_to_manifest()` to produce an empty `FeatureManifest`.
- **`populate(template_id, ...)`** — returns `None` (no exception) when the template file is missing. Passing a wrong `generated_dir` or a misspelled `template_id` both produce this silent failure.
- **`record_template_feedback(template_id, rating)`** — writes to `feedback.json` in `generated_dir`; raises `OSError` if the directory is not writable.
- **`run_maintenance(help_dir, project_root)`** — records failed feature names in `MaintenanceResult.failed`. Check `result.failed` after the call; a non-empty list means one or more features were not regenerated.

## How to diagnose

1. **Check `MaintenanceResult.failed` after `run_maintenance()`.**
   A non-empty `failed` list means specific features could not be regenerated. Re-run with `dry_run=True` first to see what `check_staleness()` reports without making changes.

2. **Call `check_staleness()` directly to isolate hash mismatches.**
   Compare `StalenessReport.stale_features` against your expected feature names. If the list is unexpectedly large, `get_changed_files(project_root)` shows which source files triggered the staleness.

3. **Confirm `populate()` receives the correct `generated_dir`.**
   When `populate()` returns `None`, call `search_by_tag()` or `list_tags()` with the same `generated_dir` to confirm templates exist there. A result of `{}` means the directory is wrong or empty.

4. **Validate `Feature` fields before generation.**
   `generate_feature_templates()` raises `ValueError: Invalid feature name: {...}` synchronously. Log `feature.name`, `feature.files`, and `feature.tags` before the call to confirm the `Feature` dataclass is populated correctly.

5. **Check `resolve_topic()` when `get_workflow_help()` returns an empty list.**
   `get_workflow_help()` relies on `resolve_topic(query, manifest)` to map a workflow name to a feature. If `resolve_topic()` returns `None`, no templates are returned. Pass your `workflow_name` to `resolve_topic()` directly and inspect the result.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`


**Tags:** `help`, `templates`, `docs`
