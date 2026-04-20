---
type: warning
feature: help-system
depth: warning
generated_at: 2026-04-20T01:18:02.573615+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Help System cautions

## What to watch for

Progressive-depth help engine and template management.

## Risk areas

The help system's progressive depth tracking and template caching can cause unexpected behavior that looks like bugs but is actually feature interaction.

- **Progressive depth state persists across lookups** — Calling `lookup_raw()` repeatedly advances depth from 0 to 1 to 2, but this state lives in the engine instance. Different test cases that share an engine will see escalated depth when they expect level 0.

- **Template file changes don't trigger automatic regeneration** — The system compares source file hashes to detect staleness, but only when you explicitly call `check_staleness()`. Modified Python files won't update their corresponding help templates until the next maintenance run.

- **Precursor warnings depend on filename patterns, not file content** — `get_precursor_warnings("models.py")` triggers database-related help based on the filename alone. Renaming files changes which warnings surface, even if the code is identical.

- **Cross-link resolution fails silently** — When `cross_links.json` references a template ID that doesn't exist on disk, `_find_template_file()` returns `None` instead of raising an exception. Broken links appear as missing sections rather than errors.

- **Feedback scoring degrades with sparse data** — `get_template_confidence()` returns lower scores when few users have rated a template. New templates start with poor confidence even if they're well-written.

## How to avoid problems

1. **Reset engine state between tests.** Create a fresh `HelpEngine()` instance for each test case, or call `reset_session()` to clear progressive depth tracking.

2. **Run staleness checks after file modifications.** Call `check_staleness()` and `run_maintenance()` when you change source files that should update help templates.

3. **Validate cross-links in CI.** Load `cross_links.json` and verify every referenced template ID resolves to a real file using `_find_template_file()`.

4. **Test with realistic feedback data.** Use `record_template_feedback()` to populate test confidence scores, or mock the feedback file with representative ratings.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
