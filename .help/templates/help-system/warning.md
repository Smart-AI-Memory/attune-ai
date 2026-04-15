---
type: warning
feature: help-system
depth: warning
generated_at: 2026-04-14T15:02:53.439274+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System cautions

## What to watch for

Template engine with automatic content generation and staleness detection.

## Risk areas

**Stale template detection failures** — The staleness system relies on source file hashes, but changes in file ordering, whitespace, or imported dependencies can cause false positives. Templates may be marked as current when their underlying code has actually changed.

**Project scanning over-discovery** — `scan_project()` uses heuristic file pattern matching that can misidentify test files, examples, or vendor code as core features. This leads to irrelevant help templates cluttering your documentation.

**Template regeneration without backup** — When `generate_feature_templates()` runs with `overwrite=True`, it permanently replaces existing templates. Any manual customizations or refinements you made will be lost without warning.

**Feedback data corruption** — Template confidence scores are stored in a shared JSON file. Concurrent access or incomplete writes can corrupt the entire feedback history, causing all templates to revert to default confidence levels.

**Path resolution inconsistencies** — Functions accept both string and Path arguments, but relative paths are resolved differently depending on the current working directory. Templates may reference wrong files when called from different contexts.

## How to avoid problems

1. **Verify staleness reports before bulk regeneration.** Run `check_staleness()` and manually inspect a few "stale" features before triggering `run_maintenance()`. False positives are common when dependencies change.

2. **Use explicit paths for template operations.** Always pass absolute paths to `generate_feature_templates()` and related functions. Relative paths can resolve incorrectly if your script changes directories.

3. **Back up manual customizations.** Before running template regeneration, copy any hand-edited templates to a safe location. The system doesn't distinguish between generated and manual content.

4. **Lock feedback file access.** If multiple processes might call `record_template_feedback()` simultaneously, implement file locking to prevent corruption of the shared feedback store.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
