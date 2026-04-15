---
type: task
feature: help-system
depth: task
generated_at: 2026-04-14T15:01:58.635957+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Work with help system

Use the help system when you need to generate documentation templates, manage project features, or track template effectiveness through feedback scoring.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/help/**`

## Steps

1. **Identify the component to modify.**
   The help system has distinct modules:
   - Template generation in `bootstrap.py`
   - Feedback tracking in `feedback.py`
   - Feature manifest management across multiple files

   Review the module's docstrings and function signatures to confirm it handles your use case.

2. **Examine existing implementations.**
   Look at how similar functions handle parameters, error conditions, and return values. For example:
   - `scan_project()` returns `ProposedFeature` objects with confidence scores
   - `record_template_feedback()` updates JSON files and returns confidence scores
   - `generate_feature_templates()` creates templates at different depth levels

3. **Implement your changes.**
   Follow the established patterns:
   - Use dataclasses for structured data (`ProposedFeature`, `GenerationResult`, etc.)
   - Handle file paths as `Path` objects or strings
   - Return meaningful error messages through exceptions
   - Include confidence scoring where applicable

4. **Test your modifications.**
   Run tests to verify functionality:
   ```bash
   pytest -k "help-system"
   ```

## Key files

- `src/attune/help/bootstrap.py` — Project scanning and feature discovery
- `src/attune/help/feedback.py` — Template feedback and usage tracking
- `src/attune/help/manifest.py` — Feature manifest loading and saving

## Verify success

Your changes work correctly when:
- Template generation produces valid markdown files with proper frontmatter
- Feedback recording updates confidence scores accurately
- Project scanning identifies features with appropriate confidence levels
- All existing tests continue to pass
