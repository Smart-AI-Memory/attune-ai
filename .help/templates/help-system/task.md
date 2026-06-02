---
type: task
name: help-system-task
feature: help-system
depth: task
generated_at: 2026-06-02T10:56:02.674680+00:00
source_hash: f28fa9280df8c251aa5a61ebcded32895a7b6d42c1aefca8dc7171d220e0ebc4
status: generated
---

# Work with the help system

Use the help system when you need to scan a project for features, generate or maintain help templates, surface progressive-depth content to users, or record and query template feedback.

## Prerequisites

- Access to the project source code
- Python environment with `attune-help` installed
- A `features.yaml` manifest in your help directory (see `load_manifest` / `save_manifest`)

## Steps

1. **Scan the project and build a feature manifest.**
   Call `scan_project()` with your project root to discover features from source files. Review the returned `ProposedFeature` list, then pass the accepted proposals to `proposals_to_manifest()` to produce a `FeatureManifest`.

   ```python
   from help.bootstrap import scan_project, proposals_to_manifest

   proposals = scan_project("path/to/project")
   manifest = proposals_to_manifest(proposals)
   ```

2. **Generate templates for each feature.**
   Pass a `Feature` object, your help directory, and the project root to `generate_feature_templates()`. Set `overwrite=True` only when you want to replace existing files. The function raises `ValueError` if the feature name is invalid.

   ```python
   from help.generator import generate_feature_templates

   result = generate_feature_templates(
       feature=manifest.features["my-feature"],
       help_dir="help/",
       project_root="path/to/project",
       overwrite=False,
   )
   print(f"Generated {len(result.templates)} template(s)")
   ```

3. **Check and repair stale templates.**
   Run `check_staleness()` to compare stored source hashes against the current state of matched files. If `StalenessReport.stale_count` is greater than zero, call `run_maintenance()` to regenerate outdated templates. Use `dry_run=True` first to preview what will change.

   ```python
   from help.staleness import check_staleness
   from help.maintenance import run_maintenance, format_status_report

   report = check_staleness(manifest, help_dir="help/", project_root="path/to/project")
   print(report.stale_features)

   result = run_maintenance("help/", "path/to/project", dry_run=True)
   print(f"Stale: {result.stale_count}, would regenerate: {result.regenerated_count}")
   ```

4. **Populate and render a template.**
   Call `populate()` with a template ID and an optional `AudienceProfile` to get a `PopulatedTemplate`. Pass the result to one of the renderer functions to produce output for your target channel.

   ```python
   from help.templates import populate, AudienceProfile
   from help.transformers import render_cli, render_claude_code

   template = populate(
       "tas-my-feature",
       audience=AudienceProfile(channel="claude-code", verbosity="normal"),
   )
   print(render_cli(template))
   ```

5. **Surface contextual help for workflows and files.**
   Use `get_workflow_help()` to retrieve relevant templates after a named workflow completes, or `get_precursor_warnings()` to surface warnings when a specific file is about to be edited.

   ```python
   from help.feedback import get_workflow_help, get_precursor_warnings

   workflow_templates = get_workflow_help("deploy", max_results=3)
   file_warnings = get_precursor_warnings("models.py", max_results=3)
   ```

6. **Record feedback and query confidence.**
   After a user rates a template, call `record_template_feedback()` with the template ID and rating. Retrieve the resulting confidence score, or call `get_template_confidence()` at any time to check a template's current score.

   ```python
   from help.feedback import record_template_feedback, get_template_confidence

   score = record_template_feedback("tas-my-feature", rating="helpful")
   print(f"Updated confidence: {score:.2f}")

   current = get_template_confidence("tas-my-feature")
   ```

7. **Verify the system is healthy.**
   Run `pytest -k "help-system"` to catch regressions across template loading, progressive depth, cross-link resolution, and renderer output. See the help system testing quickstart for full test patterns.

## Success criteria

- `generate_feature_templates()` returns a `GenerationResult` with at least one entry in `result.templates` and no feature name in `MaintenanceResult.failed`.
- `run_maintenance()` reports `regenerated_count > 0` for any features that were stale, and `stale_count` drops to zero on a second run.
- `populate()` returns a non-`None` `PopulatedTemplate`, and each renderer (`render_cli`, `render_claude_code`, `render_marketplace`) produces non-empty output.
- All `pytest -k "help-system"` tests pass.

## Key files

- `help/bootstrap.py` — `scan_project()`, `proposals_to_manifest()`
- `help/generator.py` — `generate_feature_templates()`
- `help/maintenance.py` — `run_maintenance()`, `run_hook()`, `get_changed_files()`, `format_status_report()`
- `help/staleness.py` — `check_staleness()`, `compute_source_hash()`
- `help/manifest.py` — `load_manifest()`, `save_manifest()`, `match_files_to_features()`, `resolve_topic()`
- `help/feedback.py` — `record_template_feedback()`, `get_template_confidence()`, `get_usage_weights()`, `search_by_tag()`, `list_tags()`, `get_workflow_help()`, `get_precursor_warnings()`
- `help/templates.py` — `populate()`, `AudienceProfile`, `TemplateContext`, `PopulatedTemplate`
- `help/transformers.py` — `render_cli()`, `render_claude_code()`, `render_marketplace()`
