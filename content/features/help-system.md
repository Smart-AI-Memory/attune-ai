---
feature: help-system
summary: The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help
tags: [help, templates, docs]
source_globs:
  - src/attune/help/**
nav:
  help: help-system
  mkdocs:
    how-to: how-to/help-system
    architecture: architecture/help-system
    reference: reference/help-system
---

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

## Quickstart

Serve a template that has already been generated (the ID is
`<type-prefix>-<name>`, so `con-progressive-depth` is the *concept*
named `progressive-depth`):

```python
from attune.help.templates import populate

template = populate("con-progressive-depth")
if template is not None:
    print(template.body)
```

Check whether any feature's templates are out of date:

```python
from attune.help.manifest import load_manifest
from attune.help.staleness import check_staleness

manifest = load_manifest(".help")
report = check_staleness(manifest, ".help", ".")
print(report.stale_count, "stale:", report.stale_features)
```

## Tasks

### Discover features in a project

**Goal:** turn a source tree into a feature manifest.

**Steps:**

```python
from attune.help.bootstrap import scan_project, proposals_to_manifest

proposals = scan_project(".")
manifest = proposals_to_manifest(proposals)
print([p.name for p in proposals])
```

**Verify:** `scan_project()` returns a `list[ProposedFeature]`;
`proposals_to_manifest()` returns a `FeatureManifest` mapping feature
names to their matched source files.

### Generate templates for a feature (deprecated path)

**Goal:** write depth-layered help for one feature directly from the
engine. **Prefer the single-source pipeline** (`attune-author generate
<feature> --all-kinds`); this engine call is deprecated and emits a
`DeprecationWarning`, kept as the MCP `help_update` escape hatch.

**Steps:**

```python
import warnings

from attune.help.manifest import load_manifest
from attune.help.generator import generate_feature_templates

manifest = load_manifest(".help")
feature = manifest.features["help-system"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    result = generate_feature_templates(feature, ".help", ".")
print(result)
```

**Verify:** `generate_feature_templates()` returns a `GenerationResult`
of `GeneratedTemplate` objects, each with a `source_hash`. It is
synchronous (no `await`) but warns — it writes only three depths.

### Regenerate only what's stale

**Goal:** keep templates in sync as source changes, cheaply.

**Steps:**

```python
from attune.help.maintenance import run_maintenance

result = run_maintenance(".help", ".", dry_run=False)
print(result.regenerated_count, "regenerated;", result.stale_count, "were stale")
```

**Verify:** `run_maintenance()` returns a `MaintenanceResult`. Read
`regenerated_count` and `stale_count` as **properties** (no `()`). With
`dry_run=True` it reports without rewriting.

### Find help relevant to a file or workflow

**Goal:** surface contextual help without knowing a template ID.

**Steps:**

```python
from attune.help.engine import get_precursor_warnings, get_workflow_help

for t in get_precursor_warnings("src/attune/config/unified.py"):
    print(t.template_id)
for t in get_workflow_help("security-audit"):
    print(t.template_id)
```

**Verify:** both return a `list[PopulatedTemplate]` (default
`max_results=3`). They are exported from `help.feedback` and
re-exported from `help.engine`.

## Reference

The engine is submodule-organized — there is no top-level `__all__`.
Import from the submodule that owns each symbol, or use the
`help.engine` facade for the contextual/feedback helpers.

### `help.bootstrap`

| Symbol | Purpose |
|---|---|
| `scan_project(project_root) -> list[ProposedFeature]` | Discover candidate features. |
| `proposals_to_manifest(...)` | Build a `FeatureManifest` from accepted proposals. |
| `ProposedFeature` | Discovery record. |

### `help.manifest`

| Symbol | Purpose |
|---|---|
| `load_manifest(help_dir)` / `save_manifest(...)` | Read/write the manifest. |
| `match_files_to_features(...)` | Map changed files to features. |
| `resolve_topic(query, manifest) -> str \| None` | Free-text query → feature name. |
| `Feature(name, description, files, tags, status="generated")` / `FeatureManifest` | Manifest data types. `Feature.is_manual` (true when `status == "manual"`) makes staleness/maintenance skip it. |

### `help.generator`

| Symbol | Purpose |
|---|---|
| `generate_feature_templates(feature, help_dir, project_root, depths=None, overwrite=False) -> GenerationResult` | **Deprecated.** Write 3-depth templates; emits `DeprecationWarning`. Use `attune-author generate … --all-kinds` instead. |
| `GeneratedTemplate` / `GenerationResult` | Generation outputs. |

### `help.staleness`

| Symbol | Purpose |
|---|---|
| `check_staleness(manifest, help_dir, project_root, features=None) -> StalenessReport` | Compare source hashes. |
| `compute_source_hash(...)` | Hash a feature's sources. |
| `StalenessReport` | **Properties:** `current_count`, `stale_count`, `stale_features`. |

### `help.maintenance`

| Symbol | Purpose |
|---|---|
| `run_maintenance(help_dir, project_root, features=None, dry_run=False) -> MaintenanceResult` | Regenerate stale features. |
| `run_hook(...)` | Hook-friendly wrapper (checks changed files first). |
| `format_status_report(...)` / `get_changed_files(...)` | Reporting helpers. |
| `MaintenanceResult` | **Properties:** `regenerated_count`, `stale_count`. |

### `help.templates`

| Symbol | Purpose |
|---|---|
| `populate(template_id, context=None, audience=None, *, generated_dir=None, compose=False) -> PopulatedTemplate \| None` | Resolve + populate a template. |
| `invalidate_cross_links_cache()` | Clear the cross-link resolution cache. |
| `TemplateContext` / `AudienceProfile` / `PopulatedTemplate` | Population types. |

### `help.progression`, `help.session`, `help.transformers`, `help.feedback`

| Symbol | Module | Purpose |
|---|---|---|
| `populate_progressive(template_id, ...)` | `progression` | Population that advances depth across calls. |
| `get_state` / `update_state` / `reset_session` | `session` | Per-topic session state. |
| `render_claude_code` / `render_marketplace` / `render_cli` | `transformers` | `(PopulatedTemplate) -> str`. |
| `record_template_feedback(id, rating) -> float` | `feedback` | Record a rating, return confidence. |
| `get_template_confidence(id) -> float` | `feedback` | Read confidence. |
| `get_usage_weights(days=30) -> dict` | `feedback` | Usage-weighted ranking. |
| `get_precursor_warnings(file_path, *, max_results=3)` | `feedback` | File-relevant templates. |
| `get_workflow_help(name, *, max_results=3)` | `feedback` | Workflow-relevant templates. |
| `search_by_tag(tag, *, sort_by_usage=False) -> list[str]` | `feedback` | Template IDs by tag. |
| `list_tags(*, sort_by_usage=False) -> dict[str, int]` | `feedback` | Tag → template count. |

`help.engine` is a pure facade — it defines no names of its own and
re-exports the **entire** public help API (36 symbols across all the
submodules above: data types, `scan_project`, `populate`,
`run_maintenance`, `check_staleness`, the feedback helpers, …). Import
any public symbol from its owning submodule or from `help.engine`.

## Comparison

The help engine *produces and serves* help content; other surfaces
*author* or *display* it:

| | help-system (engine) | rollout tooling | ops-dashboard help tab |
|--|----------------------|-----------------|------------------------|
| Role | Discover/generate/populate/maintain templates | Author single-source masters → project them | Display coverage + search |
| Where | `src/attune/help/` | `scripts/project_features.py`, `content/features/` | `attune.ops.help_data` |
| Entry | `import attune.help` | `python scripts/project_features.py <F>` | `python -m attune.ops` |

The engine is the runtime; the rollout tooling is the authoring
pipeline; the ops dashboard is one read-only consumer.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `TypeError: 'list' object is not callable` on `report.stale_features()` | `stale_features` is a **property**, not a method | Drop the `()` — `report.stale_features` | high |
| `populate()` returns `None` | Template ID not found in the generated directory | Confirm the ID and `generated_dir`; generate first | medium |
| Stale content served after source changed | Templates not regenerated | Run `run_maintenance(..., dry_run=False)` | medium |
| Cross-links resolve to the wrong/old target | Stale cross-link cache | `invalidate_cross_links_cache()` and retry | low |
| Progressive depth never advances | Session state keyed to a different topic | Check `help.session` state; `reset_session()` to clear | low |

### Risk areas

- **Properties vs methods.** `StalenessReport` and `MaintenanceResult`
  expose counts as properties — calling them raises `TypeError`.
- **`populate` can return `None`.** It is `PopulatedTemplate | None` —
  guard the result before using it.
- **Scope confusion.** The engine is `src/attune/help/`; the doc
  *authoring* tooling and the ops help *tab* are separate surfaces.

### Diagnosis order

1. Confirm the manifest loads: `load_manifest(".help")`.
2. Confirm the template exists: `populate("<id>")` is not `None`.
3. Rule out staleness: `check_staleness(...).stale_features`.
4. For cross-link issues: `invalidate_cross_links_cache()`.
5. For progressive depth: inspect `help.session` state.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What does the help system do?
  **A:** It discovers a project's features, generates depth-layered help
  templates for each, and serves them at runtime — adapting to the
  audience channel and advancing depth as a user asks again.
- **Q:** What are the key entry points?
  **A:** `scan_project()` (discover), `generate_feature_templates()`
  (generate), `populate()` (serve), `run_maintenance()` (keep in sync),
  and `get_precursor_warnings()` / `get_workflow_help()` (contextual).
- **Q:** How do I know if my templates are out of date?
  **A:** Call `check_staleness()` from `help.staleness`; its
  `StalenessReport.stale_features` **property** lists every feature whose
  source hash no longer matches. Then `run_maintenance()` to regenerate.
- **Q:** Is anything async?
  **A:** No — every help engine entry point is synchronous.
- **Q:** How do I find templates by tag?
  **A:** `search_by_tag(tag)` returns template IDs; `list_tags()`
  returns tag → count. Both take `sort_by_usage=True` to rank by recent
  usage.
- **Q:** Where are the source files?
  **A:** `src/attune/help/**`.

## Notes & tips

- **Import from the owning submodule** (no top-level `__all__`), or use
  the `help.engine` facade for the contextual/feedback helpers.
- **Counts are properties.** `stale_features`, `stale_count`,
  `regenerated_count`, `current_count` — no `()`.
- **`populate` is nullable.** Always check for `None`.
- **Maintenance is hash-based.** It only regenerates features whose
  source actually changed; `dry_run=True` reports without writing.

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
