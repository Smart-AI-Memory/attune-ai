---
type: error
feature: help-system
depth: error
generated_at: 2026-04-14T15:02:39.839441+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System errors

Help system errors occur during template generation, project scanning, or feedback processing operations.

## Common error signatures

- `ValueError: Invalid feature name: {...}` — Feature names contain invalid characters or formatting
- `FileNotFoundError` — Missing template files, manifest files, or source directories during generation
- `yaml.YAMLError` — Malformed features.yaml manifest during parsing
- `json.JSONDecodeError` — Corrupted feedback.json file during confidence scoring
- `OSError` — Filesystem permission issues when writing generated templates

## Where errors originate

Help system errors typically originate from these key functions:

- `generate_feature_templates()` — Raises `ValueError` for invalid feature names during template generation
- `scan_project()` — Filesystem errors when scanning project directories for feature discovery
- `record_template_feedback()` — JSON serialization errors when updating feedback scores
- `get_template_confidence()` — File access errors when reading feedback data
- `load_manifest()` — YAML parsing errors when reading features.yaml files

## How to diagnose

1. **Check feature names for validity.** If you see `ValueError: Invalid feature name`, verify that feature names contain only alphanumeric characters, hyphens, and underscores.

2. **Verify file permissions and paths.** Many errors stem from missing directories or insufficient write permissions in the help output directory. Ensure the target directory exists and is writable.

3. **Validate manifest syntax.** For YAML errors, check that your features.yaml file has correct indentation and no duplicate keys. Use a YAML validator if the error message is unclear.

4. **Inspect feedback file integrity.** If feedback operations fail, check that feedback.json exists and contains valid JSON. Delete the file if corrupted — it will be recreated with default values.

5. **Review staleness detection.** Template generation failures often occur when source files have changed but staleness detection can't compute new hashes. Ensure source files are accessible and unchanged during generation.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
