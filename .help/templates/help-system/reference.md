---
feature: help-system
depth: reference
generated_at: 2026-04-13T18:07:44.250083+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ProposedFeature` | A feature discovered by scanning. | `src/attune/help/bootstrap.py` |
| `GeneratedTemplate` | Result of generating one template file. | `src/attune/help/generator.py` |
| `GenerationResult` | Result of generating templates for a feature. | `src/attune/help/generator.py` |
| `MaintenanceResult` | Result of a help maintenance run. | `src/attune/help/maintenance.py` |
| `Feature` | A project feature mapped to source files. | `src/attune/help/manifest.py` |
| `FeatureManifest` | Parsed features.yaml manifest. | `src/attune/help/manifest.py` |
| `FeatureStaleness` | Staleness status for one feature. | `src/attune/help/staleness.py` |
| `StalenessReport` | Staleness report across all features. | `src/attune/help/staleness.py` |
| `TemplateContext` | Runtime parameters for template population. | `src/attune/help/templates.py` |
| `AudienceProfile` | Target audience for output adaptation. | `src/attune/help/templates.py` |
| `PopulatedTemplate` | Result of template population. | `src/attune/help/templates.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `scan_project()` | Scan a project and propose features. | `src/attune/help/bootstrap.py` |
| `proposals_to_manifest()` | Convert accepted proposals to a FeatureManifest. | `src/attune/help/bootstrap.py` |
| `record_template_feedback()` | Record user feedback on a template. | `src/attune/help/feedback.py` |
| `get_template_confidence()` | Get confidence score based on feedback. | `src/attune/help/feedback.py` |
| `get_usage_weights()` | Get template relevance weights from usage telemetry. | `src/attune/help/feedback.py` |
| `search_by_tag()` | Find template IDs matching a tag. | `src/attune/help/feedback.py` |
| `list_tags()` | List all tags with their template counts. | `src/attune/help/feedback.py` |
| `get_workflow_help()` | Get help templates relevant after a workflow completes. | `src/attune/help/feedback.py` |
| `get_precursor_warnings()` | Get warnings relevant to a file being edited. | `src/attune/help/feedback.py` |
| `generate_feature_templates()` | Generate help templates for a feature. | `src/attune/help/generator.py` |
| `run_maintenance()` | Run help maintenance — check staleness and regenerate. | `src/attune/help/maintenance.py` |
| `get_changed_files()` | Get files changed in the most recent commit. | `src/attune/help/maintenance.py` |
| `run_hook()` | Post-commit hook entry point. | `src/attune/help/maintenance.py` |
| `format_status_report()` | Format a staleness report for display. | `src/attune/help/maintenance.py` |
| `load_manifest()` | Load and validate features.yaml from a .help/ directory. | `src/attune/help/manifest.py` |
| `save_manifest()` | Write a FeatureManifest to features.yaml. | `src/attune/help/manifest.py` |
| `match_files_to_features()` | Match changed files against feature glob patterns. | `src/attune/help/manifest.py` |
| `resolve_topic()` | Resolve a user query to a feature name. | `src/attune/help/manifest.py` |
| `polish_template()` | Polish a generated template using an LLM. | `src/attune/help/polish.py` |
| `build_source_summary()` | Build a concise source summary for the polish prompt. | `src/attune/help/polish.py` |
| `get_preamble()` | Get the one-liner preamble for a feature. | `src/attune/help/preamble.py` |
| `get_related_preambles()` | Get preambles for features related by shared tags. | `src/attune/help/preamble.py` |
| `populate_progressive()` | Populate with type-driven depth escalation. | `src/attune/help/progression.py` |
| `get_state()` | Get the current session state (thread-safe read). | `src/attune/help/session.py` |
| `update_state()` | Update session state for a topic access. | `src/attune/help/session.py` |
| `reset_session()` | Reset progressive depth to defaults. | `src/attune/help/session.py` |
| `compute_source_hash()` | Compute SHA-256 hash of a feature's source files. | `src/attune/help/staleness.py` |
| `check_staleness()` | Check which features have stale help templates. | `src/attune/help/staleness.py` |
| `invalidate_cross_links_cache()` | Clear the cross-links cache so the next lookup re-reads disk. | `src/attune/help/templates.py` |
| `populate()` | Populate a template with context and audience adaptation. | `src/attune/help/templates.py` |
| `render_claude_code()` | Render template for inline Claude Code conversation. | `src/attune/help/transformers.py` |
| `render_marketplace()` | Render template for agentskills.io documentation page. | `src/attune/help/transformers.py` |
| `render_cli()` | Render template for terminal display via `attune help`. | `src/attune/help/transformers.py` |


## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

## Tags

`help`, `templates`, `docs`
