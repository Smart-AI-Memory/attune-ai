---
type: reference
feature: help-system
depth: reference
generated_at: 2026-04-14T15:02:09.330698+00:00
source_hash: 8d034f48405f7be88930770e7a3e4d7992e3101bb4d3cee73733ebc13fe5c521
status: generated
---

# Help System reference

## Dataclasses

### ProposedFeature

A feature discovered by scanning.

| Field | Type | Default |
|-------|------|---------|
| `name` | str | |
| `description` | str | |
| `files` | list[str] | `[]` |
| `tags` | list[str] | `[]` |
| `confidence` | str | `'medium'` |
| `reason` | str | `''` |

### GeneratedTemplate

Result of generating one template file.

| Field | Type | Default |
|-------|------|---------|
| `feature` | str | |
| `depth` | str | |
| `path` | Path | |
| `source_hash` | str | |

### GenerationResult

Result of generating templates for a feature.

| Field | Type | Default |
|-------|------|---------|
| `feature` | str | |
| `templates` | list[GeneratedTemplate] | `[]` |
| `source_hash` | str | `''` |
| `matched_files` | list[str] | `[]` |

### MaintenanceResult

Result of a help maintenance run.

| Field | Type | Default |
|-------|------|---------|
| `staleness` | StalenessReport | |
| `regenerated` | list[GenerationResult] | `[]` |
| `skipped_manual` | list[str] | `[]` |
| `failed` | list[str] | `[]` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | int | Number of stale features detected |
| `regenerated_count` | int | Number of features regenerated |

### Feature

A project feature mapped to source files.

| Field | Type | Default |
|-------|------|---------|
| `name` | str | |
| `description` | str | |
| `files` | list[str] | `[]` |
| `tags` | list[str] | `[]` |

### FeatureManifest

Parsed features.yaml manifest.

| Field | Type | Default |
|-------|------|---------|
| `version` | int | |
| `features` | dict[str, Feature] | |
| `path` | Path \| None | `None` |

### FeatureStaleness

Staleness status for one feature.

| Field | Type | Default |
|-------|------|---------|
| `feature` | str | |
| `is_stale` | bool | |
| `current_hash` | str | |
| `stored_hash` | str \| None | |
| `matched_files` | list[str] | `[]` |

### StalenessReport

Staleness report across all features.

| Field | Type | Default |
|-------|------|---------|
| `entries` | list[FeatureStaleness] | |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | int | Count of stale features |
| `current_count` | int | Count of up-to-date features |
| `stale_features` | list[str] | Names of stale features |

### TemplateContext

Runtime parameters for template population.

| Field | Type | Default |
|-------|------|---------|
| `file_path` | str \| None | `None` |
| `error_message` | str \| None | `None` |
| `workflow_name` | str \| None | `None` |
| `tool_name` | str \| None | `None` |
| `skill_name` | str \| None | `None` |
| `extra` | dict[str, Any] | `{}` |

### AudienceProfile

Target audience for output adaptation.

| Field | Type | Default |
|-------|------|---------|
| `channel` | str | `'claude-code'` |
| `verbosity` | str | `'normal'` |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|-----------|---------|--------|-------------|
| `scan_project` | `project_root: str \| Path` | list[ProposedFeature] | | Scan a project and propose features |
| `proposals_to_manifest` | `proposals: list[ProposedFeature]` | FeatureManifest | | Convert accepted proposals to a FeatureManifest |
| `record_template_feedback` | `template_id: str`, `rating: str`, `generated_dir: str \| Path \| None = None` | float | | Record user feedback on a template |
| `get_template_confidence` | `template_id: str`, `generated_dir: str \| Path \| None = None` | float | | Get confidence score based on feedback |
| `get_usage_weights` | `days: int = 30` | dict[str, float] | | Get template relevance weights from usage telemetry |
| `search_by_tag` | `tag: str`, `generated_dir: str \| Path \| None = None`, `sort_by_usage: bool = False` | list[str] | | Find template IDs matching a tag |
| `list_tags` | `generated_dir: str \| Path \| None = None`, `sort_by_usage: bool = False` | dict[str, int] | | List all tags with their template counts |
| `get_workflow_help` | `workflow_name: str`, `generated_dir: str \| Path \| None = None`, `max_results: int = 3` | list[PopulatedTemplate] | | Get help templates relevant after a workflow completes |
| `get_precursor_warnings` | `file_path: str`, `generated_dir: str \| Path \| None = None`, `max_results: int = 3` | list[PopulatedTemplate] | | Get warnings relevant to a file being edited |
| `generate_feature_templates` | `feature: Feature`, `help_dir: str \| Path`, `project_root: str \| Path`, `depths: list[str] \| None = None`, `overwrite: bool = False` | GenerationResult | ValueError — 'Invalid feature name: {...}' | Generate help templates for a feature |

## Constants

### Skip directories

| Constant | Members |
|----------|---------|
| SKIP_DIRS | `.git`, `.github`, `.help`, `.claude`, `.agents`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.tox`, `.venv`, `venv`, `env`, `node_modules`, `dist`, `build`, `.egg-info`, `htmlcov`, `site` |

### Entry point names

| Constant | Members |
|----------|---------|
| ENTRY_POINT_NAMES | `main.py`, `app.py`, `cli.py`, `server.py`, `manage.py`, `wsgi.py`, `asgi.py`, `index.ts`, `index.js`, `main.go`, `main.rs` |

### Config patterns

| Constant | Members |
|----------|---------|
| CONFIG_PATTERNS | `config`, `settings`, `conf` |

### Template depths

| Constant | Members |
|----------|---------|
| DEPTH_NAMES | `concept`, `task`, `reference` |
