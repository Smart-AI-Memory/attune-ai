---
type: note
feature: help-system
depth: note
generated_at: 2026-04-20T01:19:10.876462+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Note: help system

## Context

The help system provides progressive-depth template lookup and audience-specific adaptation for development documentation. It manages template loading, cross-link resolution, and stateful depth progression across user sessions.

## Content

The help system centers on template generation and runtime lookup through complementary classes and functions:

**Core data structures:**
- `ProposedFeature` — A feature discovered during project scanning with name, description, matched files, and confidence level
- `Feature` — A validated project feature mapped to specific source files
- `GeneratedTemplate` — Metadata for one generated template file including feature name, depth level, and content hash
- `TemplateContext` — Runtime parameters like file path, error message, and workflow name for template population
- `AudienceProfile` — Target channel and verbosity settings for output adaptation

**Generation workflow:**
- `scan_project()` analyzes source files and proposes features based on file patterns, entry points, and configuration detection
- `generate_feature_templates()` creates concept, task, and reference templates for each feature using source code analysis
- `check_staleness()` compares current source hashes against stored values to identify outdated templates

**Runtime engine:**
- `populate()` loads templates with audience-specific transformations and cross-link resolution
- `get_precursor_warnings()` surfaces relevant help when editing specific files
- `get_workflow_help()` provides context-aware assistance after workflow completion
- `record_template_feedback()` captures user ratings to improve template relevance

The system maintains session state for progressive depth (concept → task → reference) and uses file-based storage for template metadata, feedback scores, and usage telemetry.

## Source files

- `src/attune/help/**` — Core scanning and generation logic
- `packages/attune-help/src/attune_help/**` — Runtime engine and template population

**Tags:** `help`, `templates`, `docs`
