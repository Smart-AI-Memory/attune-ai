---
type: comparison
name: help-system-comparison
feature: help-system
depth: comparison
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Comparison: Help System vs Alternatives

## Context

The help system is a progressive-depth template engine that generates, populates, and maintains contextual documentation for project features. It covers the full lifecycle: scanning source code to propose features, generating templates at three depths (`concept`, `task`, `reference`), adapting output to different audiences, and tracking staleness when source files change.

## Feature comparison

The table below compares the help system's built-in entry points against two common alternatives: writing ad-hoc documentation by hand, and using a generic static-site generator.

| Capability | Help system | Hand-written docs | Generic static-site generator |
|---|---|---|---|
| Feature discovery | `scan_project()` proposes features from source automatically | Manual — you identify features yourself | Manual |
| Template generation | `generate_feature_templates()` produces concept, task, and reference depths in one call | Author each depth by hand | Typically single-depth pages |
| Progressive depth | `populate_progressive()` advances depth per session; `reset_session()` resets on topic change | Not applicable | Not applicable |
| Staleness detection | `check_staleness()` hashes source files; `run_maintenance()` regenerates stale templates automatically | No detection — drift is silent | No detection |
| Audience adaptation | `render_claude_code()`, `render_cli()`, `render_marketplace()` target specific channels from the same template | Duplicate content per channel | Requires custom theming per target |
| Contextual warnings | `get_precursor_warnings(file_path)` surfaces relevant help when a specific file is being edited | Not applicable | Not applicable |
| Workflow-triggered help | `get_workflow_help(workflow_name)` returns up to 3 relevant templates after a workflow completes | Not applicable | Not applicable |
| Feedback loop | `record_template_feedback()` updates a confidence score; `get_usage_weights()` tunes relevance over time | None | None |
| Tag-based discovery | `search_by_tag()` and `list_tags()` let you navigate templates by tag, optionally sorted by usage | Manual index maintenance | Depends on plugin |
| CI maintenance hook | `run_hook()` integrates into CI; `run_maintenance(dry_run=True)` previews changes without writing | None | None |

## When NOT to use the help system

- **Single-use scripts.** If you need one throwaway document, the overhead of defining a `Feature`, running `generate_feature_templates()`, and managing a `FeatureManifest` outweighs the benefit. Write the doc directly.
- **Content the public API doesn't expose.** The help system does not expose internals for patching. If you need behavior outside the public API (see `help.engine.__all__`), open an issue or propose an extension point rather than reaching into private modules.
- **Cross-feature orchestration.** If your documentation problem spans several features and requires coordinating their manifests, work at the orchestration layer above individual `load_manifest()` / `save_manifest()` calls rather than calling each feature's pipeline directly.
- **Non-project documentation.** `scan_project()` skips well-known non-source directories (`.git`, `node_modules`, `dist`, `build`, and others) and is designed for structured project trees. It is not a general-purpose documentation crawler.

## Use the help system when…

| Situation | Recommended entry point |
|---|---|
| You want to discover what features exist in a codebase | `scan_project()` → `proposals_to_manifest()` |
| You need concept, task, and reference docs generated for a feature | `generate_feature_templates()` |
| You want help that adapts as a user asks follow-up questions | `populate_progressive()` + `reset_session()` |
| You need to warn a user before they edit a specific file | `get_precursor_warnings(file_path)` |
| You want help surfaced automatically after a workflow finishes | `get_workflow_help(workflow_name)` |
| Your templates may drift as source files change | `check_staleness()` + `run_maintenance()` or `run_hook()` in CI |
| You need to render the same template for Claude Code, CLI, and marketplace | `render_claude_code()`, `render_cli()`, `render_marketplace()` |
| You want to measure whether a template is actually useful | `record_template_feedback()` + `get_template_confidence()` |

The help system is the right choice when you need the full pipeline — discovery, generation, population, adaptation, and maintenance — rather than any single step in isolation. If you only need one step, the corresponding module (`help.bootstrap`, `help.generator`, `help.staleness`, etc.) is importable independently.

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

**Tags:** `help`, `templates`, `docs`
