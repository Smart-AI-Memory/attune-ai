# Help System

## Overview

The help system is attune's **progressive-depth help engine** — it
discovers a project's features, generates depth-layered help templates
for each one, and serves the right level of detail based on who is
asking and what they are doing. It lives in **`src/attune/help/`** and
is organized into focused submodules (discovery, manifest, generation,
population, staleness, maintenance, feedback).

This page documents the **engine** — the Python API you call to scan,
generate, populate, and maintain help content. It is **not** the
single-source rollout tooling (`scripts/project_features.py`,
`content/features/`) that authors these very docs, and it is **not**
the ops dashboard's help tab (`attune.ops.help_data`, which only
*displays* the engine's output). Those are adjacent surfaces that
consume the engine.

The pipeline flows in four stages — **discovery → generation →
population → maintenance** — and every entry point is **synchronous**.

You reach it these ways:

- the Python API — import from the **help submodules**
  (`attune.help.bootstrap`, `attune.help.templates`,
  `attune.help.maintenance`, …); the top-level `attune.help` package
  exposes nothing, so you import from the owning submodule;
- the **`attune.help.engine`** facade — a single import surface that
  re-exports the entire public help API (36 names across the
  submodules), so `from attune.help.engine import populate,
  scan_project, run_maintenance, …` resolves them all in one place.

## Concepts

### The four-stage pipeline

| Stage | Submodule | Entry point | Produces |
|---|---|---|---|
| 1. Discovery | `help.bootstrap` | `scan_project(project_root)` | `list[ProposedFeature]` |
| 2. Generation | `help.generator` | `generate_feature_templates(...)` *(deprecated)* | `GenerationResult` |
| 3. Population | `help.templates` | `populate(template_id, ...)` | `PopulatedTemplate \| None` |
| 4. Maintenance | `help.maintenance` | `run_maintenance(help_dir, project_root)` | `MaintenanceResult` |

**Discovery** — `scan_project()` walks the project root (skipping
`.git`, `node_modules`, `__pycache__`, …) and returns `ProposedFeature`
objects (`name`, `description`, matched `files`, `tags`). Pass accepted
proposals to `proposals_to_manifest()` to build a `FeatureManifest`,
which `help.manifest` persists to `features.yaml`.

**Generation** — `generate_feature_templates()` takes a `Feature` from
the manifest and writes templates into the help directory, returning a
`GenerationResult`. **It is deprecated** — it produces only three depths
(concept/task/reference) and emits a `DeprecationWarning`; it survives
as an internal escape hatch for the MCP `help_update` tool. The current
generation path is the single-source authoring pipeline
(`attune-author generate <feature> --all-kinds` → the projector), not
this function.

**Population** — `populate(template_id, context=None, audience=None)`
resolves a template against the generated directory, applies a
`TemplateContext` (the fields `populate` honors are `file_path`,
`workflow_name`, and `error_message`), and returns a
`PopulatedTemplate` (or `None` if the ID resolves to no file).
Template IDs use the grammar **`<type-prefix>-<name>`** — e.g.
`con-progressive-depth` for the *concept* named `progressive-depth`
(prefixes: `con`/`tas`/`ref`/`qui`/`err`/`war`/`tip`/`not`/`faq`/`tro`/
`com`). `populate_progressive()` (`help.progression`) advances depth
across calls, tracking per-topic state in `help.session`.

**Maintenance** — `run_maintenance()` calls `check_staleness()`, which
hashes each feature's sources with `compute_source_hash()` and compares
to the stored hash. It returns a `MaintenanceResult`; passing
`dry_run=False` regenerates the stale features.

### Contextual entry points

Rather than resolving a template ID directly, you can ask the engine
what is relevant right now (canonical home: `help.feedback`, also
re-exported from `help.engine`):

- `get_precursor_warnings(file_path)` — up to three `PopulatedTemplate`
  objects relevant to the file about to be edited.
- `get_workflow_help(workflow_name)` — templates relevant after a named
  workflow completes.
- `resolve_topic(query, manifest)` (`help.manifest`) — maps a free-text
  query to a feature name.
- `search_by_tag(tag)` / `list_tags()` — browse the inventory by tag;
  both accept `sort_by_usage=True` to rank by recent activity.

### Properties, not methods (the gotcha)

The staleness and maintenance result objects expose **properties**, not
method calls — accessing them with `()` raises `TypeError`:

- `StalenessReport.stale_features` — the list of stale feature names.
- `StalenessReport.stale_count` / `current_count`.
- `MaintenanceResult.regenerated_count` / `stale_count`.

### Rendering and feedback

Three renderers convert a `PopulatedTemplate` into its final string
(`help.transformers`): `render_claude_code()`, `render_marketplace()`,
`render_cli()`. Every populated template can be rated:
`record_template_feedback(template_id, rating)` writes feedback and
returns the updated confidence; `get_template_confidence(template_id)`
reads it back; `get_usage_weights(days=30)` returns a `dict[str, float]`
the engine uses to rank contextual results.

### Key data types

| Type | Submodule | Role |
|---|---|---|
| `ProposedFeature` | `help.bootstrap` | Discovery output (`name`, `files`, `tags`, confidence) |
| `Feature` / `FeatureManifest` | `help.manifest` | Persistent record of features → source files (`Feature.status`/`is_manual` gates staleness) |
| `GeneratedTemplate` / `GenerationResult` | `help.generator` | Generation output (carries `source_hash`) |
| `TemplateContext` / `AudienceProfile` | `help.templates` | Runtime parameters + output channel |
| `PopulatedTemplate` | `help.templates` | Final content object for a renderer |
| `StalenessReport` | `help.staleness` | Aggregate staleness status (properties) |
| `MaintenanceResult` | `help.maintenance` | Summary of a maintenance run (properties) |

## Design & extension

### Design decisions

- **Submodule-by-stage.** Discovery, manifest, generation, population,
  staleness, maintenance, feedback each own a module so the pipeline
  stays cohesive; `help.engine` is a thin facade over the feedback
  helpers.
- **Hash-based staleness.** Each generated template records a
  `source_hash`; maintenance compares hashes so regeneration is
  incremental, not wholesale.
- **Progressive depth.** Population advances concept → task → reference
  across repeated asks, tracked per topic in `help.session`, so users
  get more detail only when they come back.
- **Channel-aware rendering.** A single `PopulatedTemplate` renders to
  Claude Code, marketplace, or CLI output via the `transformers`.

### Extension points

- **New depth or template kind:** add it to the single-source authoring
  pipeline (`attune-author` + the projector), not the deprecated
  `generate_feature_templates`.
- **New renderer/channel:** add a `render_*` transformer over
  `PopulatedTemplate`.
- **Custom contextual triggers:** build on `get_precursor_warnings` /
  `get_workflow_help` and the `get_usage_weights` ranking.
- **Hook integration:** wrap `run_hook()` / `get_changed_files()` for
  pre-commit or CI staleness checks.

<!-- attune-generated: source_hash=ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab feature=help-system kind=architecture generated_at=2026-06-24 -->
