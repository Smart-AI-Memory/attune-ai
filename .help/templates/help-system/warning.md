---
type: warning
name: help-system-warning
feature: help-system
depth: warning
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Help System Cautions

## What to watch for

The help system combines a stateful progressive-depth engine with generated templates on disk. Most surprises come from stale templates that no longer match their source, session state that persists across unrelated lookups, and confidence scores that silently reflect sparse or skewed feedback data.

## Risk areas

### Stale templates after source changes

`run_maintenance()` and `check_staleness()` compare a stored hash against the output of `compute_source_hash()`. If you add or remove files that a `Feature` tracks without updating `features.yaml`, the hash stays unchanged and stale templates are never flagged. Always update `FeatureManifest` entries — particularly the `files` list on each `Feature` — when source files move or are deleted.

### Session state bleeding across topics

`populate_progressive()` advances depth by reading and writing session state managed by `update_state()`. That state persists until you call `reset_session()`. In test suites or long-running processes, a prior lookup on one topic can leave depth at level 1 or 2, causing the next `populate_progressive()` call on a different topic to return task- or reference-depth content when concept-depth content was expected. Call `reset_session()` between unrelated test cases and at logical session boundaries in production.

### Confidence scores driven by thin feedback data

`get_template_confidence()` returns a float derived from whatever ratings `record_template_feedback()` has recorded. With few ratings, the score is volatile — a single negative rating can push a frequently used template below any confidence threshold you apply. Cross-reference `get_usage_weights()` (which draws on 30 days of usage telemetry by default) before treating confidence alone as a signal for suppressing a template.

### `generate_feature_templates()` silently skips existing files

When `overwrite=False` (the default), `generate_feature_templates()` leaves existing templates untouched even if the underlying source has changed. If you regenerate after a significant refactor without passing `overwrite=True`, users may receive help that describes the old API. Use `run_maintenance()` to detect which features are stale before deciding whether to force regeneration.

### `get_precursor_warnings()` returns an empty list for unrecognised paths

`get_precursor_warnings()` maps a `file_path` to relevant `PopulatedTemplate` results using filename and extension. Paths that don't match any feature in the manifest return an empty list with no error. If precursor warnings appear to be missing for a file type you expect to be covered, verify that the corresponding `Feature.files` patterns in `features.yaml` include that path.

### Cross-link cache is not invalidated automatically

`populate()` can compose related templates when `compose=True`. The cross-link index backing this is cached in memory. If you add or remove templates on disk during the same process lifetime, call `invalidate_cross_links_cache()` before the next `populate()` call, or the composed output may reference templates that no longer exist.

## How to avoid problems

1. **Keep `features.yaml` in sync with your source tree.** `match_files_to_features()` and `compute_source_hash()` both rely on the `files` list inside each `Feature`. An outdated manifest causes staleness detection to miss real changes.

2. **Reset session state in tests.** Add `reset_session()` to your test teardown so that progressive-depth advancement in one test doesn't affect the starting depth of the next.

3. **Pair confidence with usage data.** When using `get_template_confidence()` to rank or suppress templates, also call `get_usage_weights()` so that low-traffic templates aren't unfairly penalised by a small feedback sample.

4. **Run maintenance before regenerating.** Call `run_maintenance()` with `dry_run=True` first to see `MaintenanceResult.stale_count()` and `MaintenanceResult.regenerated_count()` without writing anything, then re-run without `dry_run` once you've confirmed the scope of changes.

5. **Depend only on the public API.** Names beginning with `_` — such as internal template-file finders and cache structures — can change without notice. Rely on the exports listed in `help.engine.__all__` to avoid breakage during refactors.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
