---
type: concept
name: help-system-concept
feature: help-system
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Help System

## How it works

The help system is a progressive-depth template engine that scans your project, generates structured help content per feature, and serves the right level of detail based on who is asking and what they are doing.

The pipeline has four stages that flow from discovery to delivery:

**1. Discovery** — `scan_project()` walks your project root (skipping directories like `.git`, `node_modules`, and `__pycache__`) and returns a list of `ProposedFeature` objects, each with a `name`, `description`, matched `files`, and a `confidence` rating. You pass accepted proposals to `proposals_to_manifest()` to produce a `FeatureManifest`, which maps feature names to their source files in `features.yaml`.

**2. Generation** — `generate_feature_templates()` takes a `Feature` from the manifest and writes one markdown file per depth level (`concept`, `task`, `reference`) into your help directory. Each output is a `GeneratedTemplate` carrying the feature name, depth, file path, and a `source_hash` that the staleness checker uses later.

**3. Population and adaptation** — `populate()` resolves a template ID against the generated directory, applies a `TemplateContext` (which can carry a `file_path`, `workflow_name`, `error_message`, or `tool_name`), and returns a `PopulatedTemplate`. `populate_progressive()` does the same but advances depth automatically across calls, tracking state through the session module. `AudienceProfile` controls the output channel (`claude-code` by default) and verbosity. Three renderers — `render_claude_code()`, `render_marketplace()`, and `render_cli()` — convert a `PopulatedTemplate` into its final string form.

**4. Maintenance** — `run_maintenance()` calls `check_staleness()`, which hashes each feature's source files with `compute_source_hash()` and compares the result to the stored hash in the manifest. Features whose source has changed appear in `StalenessReport.stale_features()`. Passing `dry_run=False` regenerates them and returns a `MaintenanceResult` with `stale_count` and `regenerated_count` properties. `run_hook()` wraps this for use in pre-commit or CI hooks by checking `get_changed_files()` first.

## Contextual entry points

Rather than resolving a template ID directly, you can ask the system what is relevant right now:

- `get_precursor_warnings(file_path)` returns up to three `PopulatedTemplate` objects relevant to the file a user is about to edit — for example, database-related warnings when opening `models.py`.
- `get_workflow_help(workflow_name)` returns templates relevant after a named workflow completes.
- `resolve_topic(query, manifest)` maps a free-text query to a feature name using the manifest.
- `search_by_tag(tag)` and `list_tags()` let you browse the template inventory by tag; both accept `sort_by_usage=True` to rank results by recent activity.

## Feedback and confidence

Every `PopulatedTemplate` can be rated. `record_template_feedback(template_id, rating)` writes to `feedback.json` in the generated directory and returns an updated confidence score. `get_template_confidence(template_id)` reads that score back. `get_usage_weights(days=30)` returns a `dict[str, float]` of template IDs weighted by how often they have been used in the last N days — the engine uses these weights to rank results from `get_workflow_help()` and `get_precursor_warnings()`.

## Key data types

| Type | Where it lives | Role in the pipeline |
|---|---|---|
| `ProposedFeature` | `help.bootstrap` | Discovery output; carries `name`, `files`, `tags`, `confidence` |
| `Feature` / `FeatureManifest` | `help.manifest` | Persistent record of features and their source files |
| `GeneratedTemplate` / `GenerationResult` | `help.generator` | Generation output; carries `source_hash` for staleness tracking |
| `TemplateContext` / `AudienceProfile` | `help.templates` | Runtime parameters and output channel for population |
| `PopulatedTemplate` | `help.templates` | Final content object passed to a renderer |
| `FeatureStaleness` / `StalenessReport` | `help.staleness` | Per-feature and aggregate staleness status |
| `MaintenanceResult` | `help.maintenance` | Summary of a maintenance run: stale, regenerated, skipped, failed |
