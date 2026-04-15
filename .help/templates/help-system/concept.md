---
type: concept
feature: help-system
depth: concept
generated_at: 2026-04-14T15:01:48.673774+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System

## How it works

The help system automatically generates documentation templates by scanning your project, tracking feature changes, and adapting output for different audiences and contexts.

The core workflow follows three phases:

- **Discovery** — `scan_project()` identifies features by analyzing entry points, configuration files, and code patterns, producing `ProposedFeature` objects with confidence scores
- **Generation** — `generate_feature_templates()` creates concept, task, and reference templates for each feature, tracking source file hashes to detect staleness
- **Maintenance** — `run_maintenance()` regenerates templates when source files change, skipping manually edited files and collecting feedback scores

The system stores templates with metadata including confidence scores from user feedback (`record_template_feedback()`), usage weights from telemetry (`get_usage_weights()`), and contextual relevance for workflows and file editing scenarios.

## What connects to it

The help system integrates with your development workflow through several touch points:

| Interface | Purpose | File |
|-----------|---------|------|
| `ProposedFeature` | Feature candidates with confidence scores from project scanning | `src/attune/help/bootstrap.py` |
| `GeneratedTemplate` | Template files linked to source hashes for staleness detection | `src/attune/help/generator.py` |
| `GenerationResult` | Batch results from template generation with matched source files | `src/attune/help/generator.py` |
| `MaintenanceResult` | Summary of regenerated, skipped, and failed templates during updates | `src/attune/help/maintenance.py` |
| `Feature` | Canonical feature definitions mapping names to source files and tags | `src/attune/help/manifest.py` |
