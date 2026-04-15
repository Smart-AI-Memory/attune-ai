---
type: note
feature: help-system
depth: note
generated_at: 2026-04-14T15:03:57.600757+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Note: help system

## Context

The help system provides template generation and maintenance for progressive-depth documentation. It scans project files to discover features, generates help templates, and tracks template quality through user feedback.

## Template lifecycle

The help system manages templates through several phases:

- **Discovery**: `scan_project()` analyzes source code to identify features and returns `ProposedFeature` instances with confidence scores
- **Manifest creation**: `proposals_to_manifest()` converts approved proposals into a `FeatureManifest` that maps features to source files
- **Template generation**: `generate_feature_templates()` creates concept, task, and reference templates for each feature, returning `GenerationResult` objects
- **Maintenance**: Staleness detection compares source file hashes to identify when templates need regeneration

## Feedback and quality tracking

The system tracks template effectiveness through usage data:

- `record_template_feedback()` captures user ratings on generated templates
- `get_template_confidence()` returns quality scores based on accumulated feedback
- `get_usage_weights()` provides relevance scores from recent template access patterns

Search functions like `search_by_tag()` and `get_workflow_help()` use these metrics to surface the most helpful templates for specific contexts.

## Data structures

Key classes represent different stages of the template lifecycle:

- `ProposedFeature` captures discovered features with confidence scores and source file associations
- `Feature` represents validated features in the manifest
- `GeneratedTemplate` tracks individual template files with source hashes for staleness detection
- `TemplateContext` provides runtime parameters for template population
- `AudienceProfile` enables output adaptation for different channels and verbosity levels

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
