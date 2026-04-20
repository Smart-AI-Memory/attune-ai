---
type: error
feature: help-system
depth: error
generated_at: 2026-04-20T01:17:47.552041+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Help System errors

Template loading, progressive depth tracking, and cross-link resolution failures in the help engine.

## Common error signatures

- `ValueError: Invalid feature name: {...}` — Feature name contains invalid characters or is empty
- `FileNotFoundError` — Template file missing during `populate()` or cross-link resolution
- `KeyError` — Missing required frontmatter field (`type`, `tags`, or `name`)
- `yaml.scanner.ScannerError` — Malformed YAML in template frontmatter
- `AttributeError: 'NoneType' object has no attribute 'body'` — Template population returned None

## Where errors originate

Help system errors typically start in these functions:

- `scan_project()` — File access errors when scanning directories or reading source files
- `generate_feature_templates()` — Template generation failures from invalid feature data or filesystem issues
- `populate()` and `populate_progressive()` — Template loading errors when files are missing or malformed
- `record_template_feedback()` and `get_template_confidence()` — JSON file corruption in feedback storage
- `_parse_template_file()` — YAML parsing errors in template frontmatter

## How to diagnose

1. **Check template file integrity.** Run `_parse_template_file()` on individual templates to isolate YAML parsing errors. Missing required fields (`type`, `tags`, `name`) cause immediate `KeyError` exceptions.

2. **Verify cross-link targets exist.** Load `cross_links.json` and test each template ID with `_find_template_file()`. Dangling references cause `FileNotFoundError` during template population.

3. **Test progressive depth state.** If depth advancement fails, check that the storage backend (memory or file-based) correctly persists session state between `lookup()` calls.

4. **Validate feature manifest.** Corrupted `features.yaml` files cause `ValueError` in `generate_feature_templates()`. Check that feature names contain only alphanumeric characters, hyphens, and underscores.

5. **Check filesystem permissions.** Template generation and feedback recording require write access to the help directory. Permission errors surface as `OSError` with specific error codes.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
