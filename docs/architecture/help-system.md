# Help System Architecture

Progressive-depth help engine and template management.

## Purpose

The help system generates, stores, populates, and serves structured help templates keyed to project features. It owns the full lifecycle: scanning source code to discover features (`scan_project`), generating templates at three depth levels (`concept`, `task`, `reference`), detecting when those templates go stale as source changes, and rendering populated templates for different output channels. It does **not** own the underlying LLM calls that produce template prose, the CLI surface that triggers maintenance, or any project-specific business logic — those concerns live outside this subsystem.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `ProposedFeature` | Candidate feature discovered by `scan_project`, carrying name, description, file list, tags, and a confidence rating before the manifest is written. | `help/bootstrap.py` |
| `Feature` | Confirmed feature from `features.yaml`, mapping a name and description to the source files it covers; the stable identity used throughout the pipeline. | `help/manifest.py` |
| `FeatureManifest` | Typed container for all `Feature` entries loaded from `features.yaml`, including the file path so callers can save changes back. | `help/manifest.py` |
| `GeneratedTemplate` | Record of one generated `.md` file: which feature and depth level produced it, where it lives on disk, and the source hash at generation time. | `help/generator.py` |
| `GenerationResult` | Aggregates all `GeneratedTemplate` instances for a single feature run, plus the source hash and matched files — the handoff from `generate_feature_templates` to maintenance. | `help/generator.py` |
| `FeatureStaleness` | Compares the stored source hash against the current hash for one feature and records which files were matched. | `help/staleness.py` |
| `StalenessReport` | Aggregates `FeatureStaleness` entries across all features; exposes `stale_count`, `current_count`, and `stale_features` for maintenance decisions. | `help/staleness.py` |
| `MaintenanceResult` | Records the outcome of `run_maintenance`: the `StalenessReport`, which features were regenerated, which were skipped (manual edits), and which failed. | `help/maintenance.py` |
| `TemplateContext` | Supplies runtime slot values (`file_path`, `workflow_name`, `error_message`, `tool_name`, `skill_name`, `extra`) when populating a template for a specific situation. | `help/templates.py` |
| `AudienceProfile` | Declares the target output channel (`claude-code` by default) and verbosity level so `populate` and the renderers can adapt tone and structure. | `help/templates.py` |
| `PopulatedTemplate` | The result of template population — a resolved, audience-adapted document ready to hand to a renderer or return directly to a caller. | `help/templates.py` |

## Data flow

Two distinct flows share the domain model. The **authoring flow** runs during project setup or CI to keep templates current. The **serving flow** runs at query time to answer a user's question.

### Authoring flow (generation and maintenance)

```
project source files
        |
        v
  scan_project()                    [help.bootstrap]
        |
        v
  list[ProposedFeature]
        |
  proposals_to_manifest()           [help.bootstrap]
        |
        v
  FeatureManifest  <--load_manifest / save_manifest-->  features.yaml
        |
        v
  compute_source_hash()             [help.staleness]
  check_staleness()
        |
        v
  StalenessReport
        |  (stale features)
        v
  generate_feature_templates()      [help.generator]
  (concept / task / reference .md files written to help_dir)
        |
        v
  GenerationResult --> MaintenanceResult
                          (run_maintenance / run_hook)  [help.maintenance]
```

### Serving flow (population and rendering)

```
query / file_path / workflow_name
        |
        v
  resolve_topic()                   [help.manifest]
        |
        v
  template_id
        |
        +----> populate()           [help.templates]
        |      or populate_progressive()  [help.progression]
        |         (uses session state from help.session)
        |
        v
  PopulatedTemplate
        |
        +----> render_cli()         [help.transformers]
        +----> render_claude_code()
        +----> render_marketplace()
        |
        v
  formatted string to caller

  Side channels:
    get_workflow_help()      [help.feedback] -- post-workflow template list
    get_precursor_warnings() [help.feedback] -- file-edit warnings
    record_template_feedback / get_template_confidence / get_usage_weights
```

## Design decisions

**Three fixed depth levels instead of arbitrary nesting.** Templates are always generated at exactly the `concept`, `task`, and `reference` levels (the `_DEPTH_NAMES` tuple). This makes progressive depth deterministic: `populate_progressive` advances through a known sequence tracked in session state, then resets on topic change. An open-ended hierarchy would require callers to reason about depth discovery, which the session layer deliberately hides.

**Source-hash-based staleness rather than file-modification timestamps.** `compute_source_hash` hashes the content of the files matched to each `Feature`. This means templates are only flagged stale when source content actually changes, not when files are touched by tooling or reformatters. The hash is stored in `GeneratedTemplate.source_hash` and checked by `FeatureStaleness`; `run_hook` uses `get_changed_files` to limit the staleness check to files reported by version control, keeping hook latency low.

**`FeatureManifest` as the single source of feature identity.** Every part of the pipeline — generation, staleness, topic resolution, precursor warnings — resolves features through `load_manifest`. Callers never construct `Feature` objects directly. This means renaming or re-scoping a feature requires only editing `features.yaml` (or re-running `scan_project` and `proposals_to_manifest`); no other module needs updating.

**Feedback and usage data kept separate from template content.** `record_template_feedback`, `get_template_confidence`, and `get_usage_weights` write to `feedback.json` alongside the generated templates. Confidence scores influence serving (e.g., `search_by_tag` with `sort_by_usage=True`) but are never baked into the `.md` files themselves. This keeps templates reproducible: regenerating from source does not erase learned quality signals.

## Extension points

- **Add a new output channel**: implement a function with the signature `render_<channel>(template: PopulatedTemplate) -> str` in `help/transformers.py`, following the pattern of `render_cli`, `render_claude_code`, and `render_marketplace`. Pass an `AudienceProfile` with the matching `channel` value to `populate`.

- **Add a new template depth level**: extend the `_DEPTH_NAMES` tuple and add a corresponding generation branch in `generate_feature_templates`. Session state in `help.session` uses the index into `_DEPTH_NAMES`, so depth advancement in `populate_progressive` will pick up the new level automatically.

- **Register a new feature without re-scanning**: call `load_manifest`, add a `Feature` entry to `manifest.features`, then call `save_manifest`. Run `generate_feature_templates` for the new feature to produce its initial templates.

- **Customize template prose quality**: replace or wrap `polish_template` in `help/polish.py`. Its `build_source_summary` helper assembles the context string passed to the LLM, so you can alter what source information influences the generated prose without changing the generation pipeline.

- **Hook maintenance into CI or pre-commit**: call `run_hook(help_dir, project_root)` — it calls `get_changed_files` internally and returns `None` if no matched features are stale, making it safe to call on every commit without unnecessary regeneration.
