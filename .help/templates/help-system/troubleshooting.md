---
type: troubleshooting
feature: help-system
depth: troubleshooting
generated_at: 2026-04-14T15:03:08.393964+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Troubleshoot help system

## Before you start

The help system provides template generation, feature discovery, and audience-specific documentation transformations. When troubleshooting, focus on the specific component that's failing: template generation, project scanning, or manifest management.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Template generation fails with validation errors | Feature name format in `generate_feature_templates()` - must not contain invalid characters |
| Project scan returns no features | Directory permissions and whether target paths match `_SKIP_DIRS` exclusions |
| Feedback scores not updating | File permissions on `feedback.json` and the generated directory structure |
| Staleness detection shows false positives | Source file content hashes using `compute_source_hash()` against stored values |
| Templates missing or empty | Feature manifest validity and whether source files exist at specified paths |

## Step-by-step diagnosis

1. **Reproduce with minimal input.**
   Create a test case with only the essential parameters. For template generation, try `generate_feature_templates()` with a single feature containing one source file.

2. **Check file system state.**
   Verify that source files exist at the paths specified in your feature manifest. Run `ls -la` on directories to confirm permissions allow reading.

3. **Validate feature data.**
   Inspect your `Feature` objects for required fields (`name`, `description`, `files`). Empty or malformed features cause silent failures in template generation.

4. **Enable debug output.**
   Check for logged errors during scanning and generation. The help system writes diagnostic information when operations fail.

5. **Test core functions individually.**
   Isolate the failing component:
   - For scanning issues: `scan_project()` with a simple directory structure
   - For template problems: `generate_feature_templates()` with a known-good feature
   - For feedback errors: `record_template_feedback()` with a valid template ID

## Common fixes

- **Fix invalid feature names.** Use only alphanumeric characters, hyphens, and underscores in feature names. Remove spaces and special characters that cause `ValueError` in `generate_feature_templates()`.

- **Update excluded directories.** If scanning misses expected files, check if they're in paths matching `_SKIP_DIRS` patterns (`.git`, `__pycache__`, `node_modules`, etc.). Move source files outside these directories or update your scan criteria.

- **Repair feedback file corruption.** Delete `feedback.json` in your generated directory and restart. The system recreates this file automatically, but corruption can cause persistent scoring errors.

- **Regenerate stale templates.** Run `run_maintenance()` to automatically detect and regenerate templates where source files have changed. This resolves most staleness-related issues.

- **Check Python version compatibility.** The help system uses dataclass features that require Python 3.7+. Upgrade if you're running an older version.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
