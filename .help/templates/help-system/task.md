---
type: task
feature: help-system
depth: task
generated_at: 2026-04-20T01:16:47.605919+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Work with help system

Use the help system when you need to modify template discovery, generate feature documentation, or adjust feedback scoring for user queries.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/help/` and `packages/attune-help/src/attune_help/`

## Identify the component to modify

The help system has distinct responsibilities spread across modules:

- **Project scanning**: `bootstrap.py` discovers features and generates manifests
- **Feedback tracking**: `feedback.py` records user ratings and calculates confidence scores
- **Template population**: Template engine populates content with project-specific data
- **Template generation**: Creates markdown files from feature definitions

Review the module docstrings and function signatures to locate the exact component you need to change.

## Scan project features

To modify how features are discovered:

1. Open `src/attune/help/bootstrap.py`
2. Examine `scan_project()` to understand current detection logic
3. Modify the scanning rules in `_SKIP_DIRS`, `_ENTRY_POINT_NAMES`, or `_CONFIG_PATTERNS` constants
4. Update `ProposedFeature` creation logic if you need different metadata

## Adjust feedback and confidence

To modify user feedback handling:

1. Open `src/attune/help/feedback.py`
2. Use `record_template_feedback()` to change how ratings are stored
3. Modify `get_template_confidence()` to adjust scoring algorithms
4. Update `get_usage_weights()` to change template ranking based on telemetry

## Generate or regenerate templates

To create new templates or update existing ones:

1. Use `generate_feature_templates()` with a `Feature` object and target directory
2. Set `overwrite=True` to replace existing files
3. Specify `depths` parameter to control which template types are generated (concept, task, reference)
4. Check the returned `GenerationResult` for success status

## Test your changes

Run the help system test suite to verify your modifications:

```bash
pytest tests/help/ -v
```

Focus on tests related to your specific component:
- Template loading and parsing tests
- Progressive depth advancement tests
- Cross-link resolution tests
- Renderer output validation tests

## Verify the integration works

Your changes work correctly when:
- `scan_project()` discovers all intended features without errors
- Template generation produces valid markdown files with proper frontmatter
- Feedback recording updates confidence scores as expected
- Cross-links resolve to existing templates
- All renderers produce well-formed output
