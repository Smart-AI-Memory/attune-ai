---
type: task
feature: help-system
depth: task
generated_at: 2026-05-04T02:30:49.174182+00:00
source_hash: 02f860e914d05f44ecfe133be87b26cad7e3f200e70a1a30901af220c56e2181
status: generated
---

# Work with help system

Use the help system when you need to modify template generation, add feedback scoring, or maintain the progressive-depth help engine.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/help/` and `packages/attune-help/src/attune_help/`

## Find the right module

1. **Identify your change type.**
   The help system has distinct modules for different responsibilities:
   - **Bootstrap**: Project scanning and feature discovery (`bootstrap.py`)
   - **Feedback**: Template scoring and usage analytics (`feedback.py`)
   - **Generation**: Template creation from features (`generation.py`)
   - **Templates**: Template population and rendering (`templates.py`)

2. **Locate the target function.**
   Read the function's docstring and parameters to confirm it handles your use case:
   - `scan_project()` — Discovers features by analyzing project files
   - `generate_feature_templates()` — Creates help templates from a feature definition
   - `record_template_feedback()` — Stores user ratings for template quality
   - `get_template_confidence()` — Calculates confidence scores from feedback data
   - `search_by_tag()` — Finds templates matching specific tags

## Make the change

1. **Review existing patterns.**
   Check how similar functions in the same module handle parameters, return values, and error cases.

2. **Implement your modification.**
   Follow the module's conventions for naming, error handling, and data structures.

3. **Update related data classes.**
   If you modify function signatures, ensure dataclasses like `GenerationResult`, `FeatureStaleness`, or `AudienceProfile` remain consistent.

## Verify the change

1. **Run targeted tests.**
   Execute tests for the specific module you modified:
   ```bash
   pytest tests/help/test_bootstrap.py  # for bootstrap changes
   pytest tests/help/test_feedback.py   # for feedback changes
   ```

2. **Test template generation.**
   Verify that template creation still works end-to-end:
   ```bash
   python -m attune_help.cli generate-templates
   ```

You'll know the change worked when tests pass and the help system continues to generate valid templates with proper frontmatter and cross-links.

## Key files

- `src/attune/help/bootstrap.py` — Project scanning and feature discovery
- `src/attune/help/feedback.py` — Template feedback and confidence scoring
- `src/attune/help/generation.py` — Template file generation
- `packages/attune-help/src/attune_help/templates.py` — Template population and rendering
