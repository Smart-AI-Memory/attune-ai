---
type: reference
feature: help-system
depth: reference
generated_at: 2026-05-04T02:31:02.392786+00:00
source_hash: 02f860e914d05f44ecfe133be87b26cad7e3f200e70a1a30901af220c56e2181
status: generated
---

# Help System API reference

The help system provides template generation, progressive depth navigation, and audience-specific rendering for project documentation.

## Dataclasses

| Class | Description |
|-------|-------------|
| `ProposedFeature` | A feature discovered by project scanning |
| `GeneratedTemplate` | Result of generating one template file |
| `GenerationResult` | Result of generating templates for a feature |
| `MaintenanceResult` | Result of a help maintenance run |
| `Feature` | A project feature mapped to source files |
| `FeatureManifest` | Parsed features.yaml manifest |
| `FeatureStaleness` | Staleness status for one feature |
| `StalenessReport` | Staleness report across all features |
| `TemplateContext` | Runtime parameters for template population |
| `AudienceProfile` | Target audience for output adaptation |

### ProposedFeature fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Feature name |
| `description` | `str` | — | Feature description |
| `files` | `list[str]` | `[]` | Associated source files |
| `tags` | `list[str]` | `[]` | Classification tags |
| `confidence` | `str` | `'medium'` | Discovery confidence level |
| `reason` | `str` | `''` | Rationale for the feature |

### GeneratedTemplate fields

| Field | Type | Description |
|-------|------|-------------|
| `feature` | `str` | Feature name |
| `depth` | `str` | Template depth level |
| `path` | `Path` | File system path |
| `source_hash` | `str` | SHA-256 of source files |

### GenerationResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature` | `str` | — | Feature name |
| `templates` | `list[GeneratedTemplate]` | `[]` | Generated template files |
| `source_hash` | `str` | `''` | SHA-256 of source files |
| `matched_files` | `list[str]` | `[]` | Files matched during generation |

### MaintenanceResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `staleness` | `StalenessReport` | — | Staleness analysis results |
| `regenerated` | `list[GenerationResult]` | `[]` | Features that were regenerated |
| `skipped_manual` | `list[str]` | `[]` | Manually authored templates skipped |
| `failed` | `list[str]` | `[]` | Features that failed regeneration |

### MaintenanceResult properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Number of stale features detected |
| `regenerated_count` | `int` | Number of features regenerated |

### Feature fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Feature name |
| `description` | `str` | — | Feature description |
| `files` | `list[str]` | `[]` | Source file patterns |
| `tags` | `list[str]` | `[]` | Classification tags |

### FeatureManifest fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | `int` | — | Manifest schema version |
| `features` | `dict[str, Feature]` | — | Feature definitions |
| `path` | `Path \| None` | `None` | Manifest file path |

### FeatureStaleness fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature` | `str` | — | Feature name |
| `is_stale` | `bool` | — | Whether templates are outdated |
| `current_hash` | `str` | — | Current source file hash |
| `stored_hash` | `str \| None` | — | Previously stored hash |
| `matched_files` | `list[str]` | `[]` | Files matched to this feature |

### StalenessReport fields

| Field | Type | Description |
|-------|------|-------------|
| `entries` | `list[FeatureStaleness]` | Staleness status per feature |

### StalenessReport properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Count of stale features |
| `current_count` | `int` | Count of up-to-date features |
| `stale_features` | `list[str]` | Names of stale features |

### TemplateContext fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_path` | `str \| None` | `None` | File being edited |
| `error_message` | `str \| None` | `None` | Error context |
| `workflow_name` | `str \| None` | `None` | Workflow that completed |
| `tool_name` | `str \| None` | `None` | Tool being documented |
| `skill_name` | `str \| None` | `None` | Skill being documented |
| `extra` | `dict[str, Any]` | `{}` | Additional context data |

### AudienceProfile fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `channel` | `str` | `'claude-code'` | Output channel |
| `verbosity` | `str` | `'normal'` | Detail level |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `scan_project` | `project_root: str \| Path` | `list[ProposedFeature]` | Scan a project and propose features |
| `proposals_to_manifest` | `proposals: list[ProposedFeature]` | `FeatureManifest` | Convert accepted proposals to a FeatureManifest |
| `record_template_feedback` | `template_id: str, rating: str, *, generated_dir: str \| Path \| None = None` | `float` | Record user feedback on a template |
| `get_template_confidence` | `template_id: str, *, generated_dir: str \| Path \| None = None` | `float` | Get confidence score based on feedback |
| `get_usage_weights` | `days: int = 30` | `dict[str, float]` | Get template relevance weights from usage telemetry |
| `search_by_tag` | `tag: str, *, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `list[str]` | Find template IDs matching a tag |
| `list_tags` | `*, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `dict[str, int]` | List all tags with their template counts |
| `get_workflow_help` | `workflow_name: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get help templates relevant after a workflow completes |
| `get_precursor_warnings` | `file_path: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get warnings relevant to a file being edited |
| `generate_feature_templates` | `feature: Feature, help_dir: str \| Path, project_root: str \| Path, depths: list[str] \| None = None, overwrite: bool = False` | `GenerationResult` | Generate help templates for a feature |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `generate_feature_templates` | `ValueError` | `'Invalid feature name: {...}'` |

## Constants

### Skip directories

| Constant | Values |
|----------|--------|
| `_SKIP_DIRS` | `'.git'`, `'.github'`, `'.help'`, `'.claude'`, `'.agents'`, `'__pycache__'`, `'.mypy_cache'`, `'.pytest_cache'`, `'.ruff_cache'`, `'.tox'`, `'.venv'`, `'venv'`, `'env'`, `'node_modules'`, `'dist'`, `'build'`, `'.egg-info'`, `'htmlcov'`, `'site'` |

### Entry point patterns

| Constant | Values |
|----------|--------|
| `_ENTRY_POINT_NAMES` | `'main.py'`, `'app.py'`, `'cli.py'`, `'server.py'`, `'manage.py'`, `'wsgi.py'`, `'asgi.py'`, `'index.ts'`, `'index.js'`, `'main.go'`, `'main.rs'` |

### Configuration patterns

| Constant | Values |
|----------|--------|
| `_CONFIG_PATTERNS` | `'config'`, `'settings'`, `'conf'` |

### Template depth levels

| Constant | Values |
|----------|--------|
| `_DEPTH_NAMES` | `'concept'`, `'task'`, `'reference'` |
