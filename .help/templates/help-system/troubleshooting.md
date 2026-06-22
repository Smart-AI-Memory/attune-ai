---
type: troubleshooting
name: help-system-troubleshooting
feature: help-system
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Troubleshoot help system

## Before you start

The help system has two layers that can fail independently: the **manifest layer** (feature discovery, `features.yaml`, staleness tracking) and the **template layer** (population, progressive depth, cross-link resolution, rendering). Identify which layer the failure is in before diving into code.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `populate()` or `populate_progressive()` returns `None` | Confirm the template ID exists: call `search_by_tag()` or inspect the generated directory for the matching `.md` file |
| `generate_feature_templates()` raises `ValueError: Invalid feature name` | Verify `Feature.name` contains no path separators or unsupported characters before passing it to `generate_feature_templates()` |
| `check_staleness()` reports every feature as stale after no code change | Compare `FeatureStaleness.current_hash` vs `FeatureStaleness.stored_hash`; a missing or corrupt `features.yaml` resets all stored hashes |
| `run_maintenance()` shows `MaintenanceResult.regenerated_count` of 0 but stale features remain | Check `MaintenanceResult.skipped_manual` and `MaintenanceResult.failed`; manually edited templates are skipped by default |
| `get_precursor_warnings()` returns an empty list for a file you expect to match | Confirm `match_files_to_features()` maps that file to at least one feature; files outside the manifest's tracked paths produce no warnings |
| `get_workflow_help()` returns irrelevant templates | Call `resolve_topic()` with the same `workflow_name` to see which feature the manifest resolves to; the mismatch is usually in `FeatureManifest.features` |
| Cross-link resolution silently drops links | Call `invalidate_cross_links_cache()` to force a cache rebuild, then re-run `populate()` |
| `get_template_confidence()` returns an unexpected score | Inspect `feedback.json` in your generated directory; stale or corrupt feedback entries skew the score |
| Renderers (`render_cli`, `render_claude_code`, `render_marketplace`) produce empty output | Confirm `populate()` returned a non-`None` `PopulatedTemplate` before passing it to the renderer |

## Step-by-step diagnosis

1. **Reproduce the failure with a minimal call.**
   Strip the failing call to its required arguments and run it in isolation. For example, if `populate()` misbehaves, call it directly with only `template_id` and a bare `AudienceProfile()` — no extra context — and confirm the failure still occurs.

2. **Check the manifest is valid.**
   Load the manifest explicitly and inspect it:
   ```python
   from help.manifest import load_manifest
   manifest = load_manifest("your/help_dir")
   print(manifest.version, list(manifest.features.keys()))
   ```
   A `KeyError` or empty `features` dict means `features.yaml` is missing, malformed, or was never written by `save_manifest()`.

3. **Check staleness state.**
   Run a dry-run maintenance pass to see what the system considers stale without making changes:
   ```python
   from help.maintenance import run_maintenance
   result = run_maintenance("your/help_dir", "your/project_root", dry_run=True)
   print(result.stale_count, result.staleness.stale_features())
   ```
   If `stale_features()` lists features you didn't change, compare `FeatureStaleness.current_hash` with `FeatureStaleness.stored_hash` to find which source files changed.

4. **Inspect changed files.**
   ```python
   from help.maintenance import get_changed_files, format_status_report
   from help.staleness import check_staleness
   from help.manifest import load_manifest

   manifest = load_manifest("your/help_dir")
   changed = get_changed_files("your/project_root")
   report = check_staleness(manifest, "your/help_dir", "your/project_root")
   print(format_status_report(report))
   ```
   This confirms which files triggered staleness and which features they map to via `match_files_to_features()`.

5. **Reset session state if depth is stuck.**
   Progressive depth is stateful. If `populate_progressive()` always returns the same depth level, call `reset_session()` and retry:
   ```python
   from help.engine import reset_session
   reset_session()
   ```

6. **Run the help system tests.**
   ```
   pytest -k "help" -v --tb=short
   ```
   If a test covers the failing path, its fixtures give you a reproducible starting point. Pay particular attention to tests covering `populate()`, `check_staleness()`, and `run_maintenance()`.

## Common fixes

- **Missing or stale `features.yaml`.**
  Regenerate it from a fresh scan:
  ```python
  from help.bootstrap import scan_project, proposals_to_manifest
  from help.manifest import save_manifest

  proposals = scan_project("your/project_root")
  manifest = proposals_to_manifest(proposals)
  save_manifest(manifest, "your/help_dir")
  ```

- **Template not found after generation.**
  If `populate()` returns `None` for a template you just generated, confirm `overwrite=True` was passed to `generate_feature_templates()` when regenerating, and that the `help_dir` path you pass to `populate()` matches the one used during generation.

- **Stale cross-link cache.**
  Call `invalidate_cross_links_cache()` from `help.templates` after adding or removing templates. The cache is not invalidated automatically when files change on disk.

- **Corrupt or missing `feedback.json`.**
  If `get_template_confidence()` raises or returns nonsensical values, delete `feedback.json` from the generated directory. The file is recreated on the next `record_template_feedback()` call.

- **Dependency version mismatch.**
  If behavior changed after a dependency upgrade, run `pip show <package>` to confirm the installed version. The manifest format (`features.yaml` version field: `FeatureManifest.version`) can also vary between releases — check that the version integer matches what your installed code expects.

- **Manually edited templates blocking regeneration.**
  `run_maintenance()` skips templates listed in `MaintenanceResult.skipped_manual`. To force regeneration, call `generate_feature_templates()` directly with `overwrite=True`.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`


**Tags:** `help`, `templates`, `docs`
