# Help System

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

<!-- attune-generated: source_hash=ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab feature=help-system kind=how-to generated_at=2026-06-24 -->
