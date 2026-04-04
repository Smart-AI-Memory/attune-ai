---
feature: help-system
depth: reference
generated_at: 2026-04-04T02:25:50.376175+00:00
source_hash: cb73fad6d8cdda9b027176f7e3c046b7f6e2d022d3546db534c3ab1b0d741b0b
status: generated
---

# Help System Reference

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

| `HelpEngine` | Lightweight help runtime with progressive depth. | `packages/attune-help/src/attune_help/engine.py` |

| `SessionStorage` | Protocol for session state backends. | `packages/attune-help/src/attune_help/storage.py` |

| `LocalFileStorage` | File-based session storage (default implementation). | `packages/attune-help/src/attune_help/storage.py` |

| `TemplateContext` | Runtime parameters for template population. | `packages/attune-help/src/attune_help/templates.py` |

| `AudienceProfile` | Target audience for output adaptation. | `packages/attune-help/src/attune_help/templates.py` |

| `PopulatedTemplate` | Result of template population. | `packages/attune-help/src/attune_help/templates.py` |


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

| `get_feature()` | Look up a feature by name. | `src/attune/help/manifest.py` |

| `resolve_topic()` | Resolve a user query to a feature name. | `src/attune/help/manifest.py` |

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

| `populate_progressive()` | Populate with type-driven depth escalation. | `packages/attune-help/src/attune_help/progression.py` |

| `invalidate_cross_links_cache()` | Clear the cross-links cache so the next lookup re-reads disk. | `packages/attune-help/src/attune_help/templates.py` |

| `populate()` | Populate a template with context and audience adaptation. | `packages/attune-help/src/attune_help/templates.py` |

| `render_claude_code()` | Render template for inline Claude Code conversation. | `packages/attune-help/src/attune_help/transformers.py` |

| `render_marketplace()` | Render template for static site documentation. | `packages/attune-help/src/attune_help/transformers.py` |

| `render_cli()` | Render template for terminal display. | `packages/attune-help/src/attune_help/transformers.py` |


## Source Files

- `src/attune/help/**`

- `packages/attune-help/src/attune_help/**`


## Tags

`help`, `templates`, `docs`
