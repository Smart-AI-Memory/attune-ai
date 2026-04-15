---
type: tip
feature: help-system
depth: tip
generated_at: 2026-04-14T15:03:48.989930+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Tip: working effectively with help system

## Context

Progressive-depth help engine and template management.

## Recommendations

1. **Start with `scan_project()` for discovery, not manual file analysis.** The scanner identifies features by examining entry points, config patterns, and directory structure — it catches patterns you might miss.

2. **Use the feedback system to improve template relevance over time.** Call `record_template_feedback()` after users interact with generated templates — the confidence scores from `get_template_confidence()` help prioritize which templates need attention.

3. **Let the staleness checker drive your maintenance cycles.** Check `StalenessReport.stale_count` before regenerating templates — source hash comparison prevents unnecessary work when files haven't changed.

## Why this matters

The help system is designed around automated discovery and incremental improvement rather than manual curation. Working against this design means rebuilding features that already exist and missing the feedback loops that make templates better over time.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
