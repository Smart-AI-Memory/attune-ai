---
type: note
name: help-system-note
feature: help-system
depth: note
generated_at: 2026-06-02T10:56:02.713979+00:00
source_hash: f28fa9280df8c251aa5a61ebcded32895a7b6d42c1aefca8dc7171d220e0ebc4
status: generated
---

# Note: help system

## Context

The help system is a progressive-depth template engine. It scans your project to discover features, generates and maintains per-feature help templates at three depth levels (`concept`, `task`, `reference`), and adapts output for different audiences and rendering targets.

## Public surface

The `help.engine` module re-exports the full public API. The surface splits into two cooperating layers.

**Data classes** represent the domain objects that flow between functions:

| Class | Module | Represents |
|---|---|---|
| `ProposedFeature` | `help.bootstrap` | A feature discovered during project scanning |
| `Feature` | `help.manifest` | A project feature mapped to its source files |
| `FeatureManifest` | `help.manifest` | The parsed `features.yaml` manifest |
| `GeneratedTemplate` | `help.generator` | A single generated template file with its source hash |
| `GenerationResult` | `help.generator` | All templates generated for one feature |
| `MaintenanceResult` | `help.maintenance` | The outcome of a maintenance run, including `stale_count` and `regenerated_count` |
| `StalenessReport` | `help.staleness` | Per-feature staleness status across a manifest |
| `AudienceProfile` | `help.templates` | Target channel and verbosity for rendered output |
| `TemplateContext` | `help.templates` | Runtime parameters (file path, workflow name, error message, etc.) passed to `populate` |
| `PopulatedTemplate` | `help.templates` | A template with all context slots filled, ready for rendering |

**Top-level functions** accept and return those classes. A few representative examples:

- `scan_project()` → `list[ProposedFeature]`; feed the result to `proposals_to_manifest()` to produce a `FeatureManifest`.
- `generate_feature_templates(feature, help_dir, project_root)` → `GenerationResult`; pass `overwrite=True` to replace existing files.
- `run_maintenance(help_dir, project_root)` → `MaintenanceResult`; set `dry_run=True` to preview changes without writing.
- `populate(template_id, context, audience)` → `PopulatedTemplate`; pass to `render_cli()`, `render_claude_code()`, or `render_marketplace()` for channel-specific output.
- `get_precursor_warnings(file_path)` and `get_workflow_help(workflow_name)` return `list[PopulatedTemplate]` ranked by relevance.
- `record_template_feedback(template_id, rating)` updates the confidence score returned by `get_template_confidence()`.

## Session state

`populate_progressive()` tracks which depth level (`0` = concept, `1` = task, `2` = reference) the current session has reached for a given topic. Call `reset_session()` to clear that state — for example, between test runs or when the user switches topics.

## Rendering targets

Three renderers in `help.transformers` adapt a `PopulatedTemplate` for different surfaces: `render_cli()`, `render_claude_code()`, and `render_marketplace()`. The `AudienceProfile.channel` field defaults to `'claude-code'`.

**Tags:** `help`, `templates`, `docs`
