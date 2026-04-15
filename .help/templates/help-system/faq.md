---
type: faq
feature: help-system
depth: faq
generated_at: 2026-04-14T15:03:29.251078+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System FAQ

## What is the help system?

A template engine that generates documentation from source code and manages audience-specific help content.

## When should I use the help system?

Use the help system when you need to:
- Generate documentation templates automatically from source files
- Track which help content is outdated
- Get contextual help suggestions based on your current workflow
- Manage multi-depth documentation (concept, task, reference)

## What are the main functions?

Start with these key functions:

- `scan_project()` — Discovers features in your project and proposes documentation structure
- `generate_feature_templates()` — Creates help templates for a specific feature
- `get_workflow_help()` — Returns relevant help after completing a workflow
- `check_staleness()` — Identifies which templates need updating

## How do I get started?

1. Run `scan_project()` on your project root to discover features
2. Convert the proposals to a manifest with `proposals_to_manifest()`
3. Generate templates with `generate_feature_templates()` for each feature

## What's a feature manifest?

A `features.yaml` file that maps your project's features to their source files. The help system uses this to track which documentation corresponds to which code.

## How does staleness detection work?

The system computes a hash of each feature's source files. When you run `check_staleness()`, it compares the current hash to the stored hash to identify outdated templates.

## How do I debug help system issues?

Run `pytest -k "help-system" -v` first. If tests pass but your code fails, add logging at the failure point and check for:
- Missing `features.yaml` manifest
- Invalid feature names in `generate_feature_templates()`
- File path issues in template generation

## Where are the source files?

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
