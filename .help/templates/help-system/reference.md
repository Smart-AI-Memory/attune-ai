---
type: reference
feature: help-system
depth: reference
generated_at: 2026-04-20T01:17:02.687618+00:00
source_hash: 6d2c6cea2e90c550773fa55099fbf9d667aaf6f0539f84b791fb4828abba3c47
status: generated
---

# Help System API reference

Generate templates, track staleness, provide contextual help, and adapt output for different audiences.

## Core Classes

### Data structures

| Class | Description |
|-------|-------------|
| `ProposedFeature` | A feature discovered by scanning |
| `GeneratedTemplate` | Result of generating one template file |
| `GenerationResult` | Result of generating templates for a feature |
| `MaintenanceResult` | Result of a help maintenance run |
| `Feature` | A project feature mapped to source files |
| `FeatureManifest` | Parsed features.yaml manifest |
| `FeatureStaleness` | Staleness status for one feature |
| `StalenessReport` | Staleness report across all features |
| `TemplateContext` | Runtime parameters for template population |
| `AudienceProfile` | Target audience for output adaptation |
| `PopulatedTemplate` | Result of template population |

### ProposedFeature fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Feature name |
| `description` | `str` | | Feature description |
| `files` | `list[str]` | `[]` | Source files |
| `tags` | `list[str]` | `[]` | Classification tags |
| `confidence` | `str` | `'medium'` | Confidence level |
| `reason` | `str` | `''` | Justification text |

### GeneratedTemplate fields

| Field | Type | Description |
|-------|------|-------------|
| `feature` | `str` | Feature name |
| `depth` | `str` | Template depth level |
| `path` | `Path` | File path |
| `source_hash` | `str` | Content hash |

### GenerationResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature` | `str` | | Feature name |
| `templates` | `list[GeneratedTemplate]` | `[]` | Generated templates |
| `source_hash` | `str` | `''` | Source content hash |
| `matched_files` | `list[str]` | `[]` | Files that triggered generation |

### MaintenanceResult fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `staleness` | `StalenessReport` | | Staleness analysis |
| `regenerated` | `list[GenerationResult]` | `[]` | Regenerated features |
| `skipped_manual` | `list[str]` | `[]` | Manually maintained features |
| `failed` | `list[str]` | `[]` | Failed regenerations |

### MaintenanceResult properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Number of stale features detected |
| `regenerated_count` | `int` | Number of features regenerated |

### Feature fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Feature name |
| `description` | `str` | | Feature description |
| `files` | `list[str]` | `[]` | Source files |
| `tags` | `list[str]` | `[]` | Classification tags |

### FeatureManifest fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `version` | `int` | | Manifest version |
| `features` | `dict[str, Feature]` | | Feature definitions |
| `path` | `Path \| None` | `None` | Manifest file path |

### FeatureStaleness fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature` | `str` | | Feature name |
| `is_stale` | `bool` | | Whether feature is stale |
| `current_hash` | `str` | | Current content hash |
| `stored_hash` | `str \| None` | | Previously stored hash |
| `matched_files` | `list[str]` | `[]` | Files that match this feature |

### StalenessReport fields

| Field | Type | Description |
|-------|------|-------------|
| `entries` | `list[FeatureStaleness]` | Staleness entries |

### StalenessReport properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Count of stale features |
| `current_count` | `int` | Count of up-to-date features |
| `stale_features` | `list[str]` | Names of stale features |

### TemplateContext fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_path` | `str \| None` | `None` | Context file path |
| `error_message` | `str \| None` | `None` | Error context |
| `workflow_name` | `str \| None` | `None` | Workflow context |
| `tool_name` | `str \| None` | `None` | Tool context |
| `skill_name` | `str \| None` | `None` | Skill context |
| `extra` | `dict[str, Any]` | `{}` | Additional context |

### AudienceProfile fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `channel` | `str` | `'claude-code'` | Output channel |
| `verbosity` | `str` | `'normal'` | Detail level |

## Functions

### Project scanning

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `scan_project` | `project_root: str \| Path` | `list[ProposedFeature]` | Scan a project and propose features |
| `proposals_to_manifest` | `proposals: list[ProposedFeature]` | `FeatureManifest` | Convert accepted proposals to a FeatureManifest |

### Template feedback and discovery

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `record_template_feedback` | `template_id: str, rating: str, *, generated_dir: str \| Path \| None = None` | `float` | Record user feedback on a template |
| `get_template_confidence` | `template_id: str, *, generated_dir: str \| Path \| None = None` | `float` | Get confidence score based on feedback |
| `get_usage_weights` | `days: int = 30` | `dict[str, float]` | Get template relevance weights from usage telemetry |
| `search_by_tag` | `tag: str, *, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `list[str]` | Find template IDs matching a tag |
| `list_tags` | `*, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `dict[str, int]` | List all tags with their template counts |
| `get_workflow_help` | `workflow_name: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get help templates relevant after a workflow completes |
| `get_precursor_warnings` | `file_path: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get warnings relevant to a file being edited |

### Template generation

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `generate_feature_templates` | `feature: Feature, help_dir: str \| Path, project_root: str \| Path, depths: list[str] \| None = None, overwrite: bool = False` | `GenerationResult` | `ValueError` — 'Invalid feature name: {...}' | Generate help templates for a feature |

### Maintenance and staleness

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_maintenance` | | | Run help maintenance — check staleness and regenerate |
| `get_changed_files` | | | Get files changed in the most recent commit |
| `run_hook` | | | Post-commit hook entry point |
| `format_status_report` | | | Format a staleness report for display |
| `compute_source_hash` | | | Compute SHA-256 hash of a feature's source files |
| `check_staleness` | | | Check which features have stale help templates |

### Manifest management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_manifest` | | | Load and validate features.yaml from a .help/ directory |
| `save_manifest` | | | Write a FeatureManifest to features.yaml |
| `match_files_to_features` | | | Match changed files against feature glob patterns |
| `resolve_topic` | | | Resolve a user query to a feature name |

### Template processing

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `polish_template` | | | Polish a generated template using an LLM |
| `build_source_summary` | | | Build a concise source summary for the polish prompt |
| `get_preamble` | | | Get the one-liner preamble for a feature |
| `get_related_preambles` | | | Get preambles for features related by shared tags |
| `populate_progressive` | | | Populate with type-driven depth escalation |
| `populate` | | | Populate a template with context and audience adaptation |
| `invalidate_cross_links_cache` | | | Clear the cross-links cache so the next lookup re-reads disk |

### Session management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_state` | | | Get the current session state (thread-safe read) |
| `update_state` | | | Update session state for a topic access |
| `reset_session` | | | Reset progressive depth to defaults |

### Output renderers

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `render_claude_code` | | | Render template for inline Claude Code conversation |
| `render_marketplace` | | | Render template for agentskills.io documentation page |
| `render_cli` | | | Render template for terminal display via `attune help` |

## Constants

### Skip directories

| Constant | Values |
|----------|--------|
| `_SKIP_DIRS` | `.git`, `.github`, `.help`, `.claude`, `.agents`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.tox`, `.venv`, `venv`, `env`, `node_modules`, `dist`, `build`, `.egg-info`, `htmlcov`, `site` |

### Entry point names

| Constant | Values |
|----------|--------|
| `_ENTRY_POINT_NAMES` | `main.py`, `app.py`, `cli.py`, `server.py`, `manage.py`, `wsgi.py`, `asgi.py`, `index.ts`, `index.js`, `main.go`, `main.rs` |

### Config patterns

| Constant | Values |
|----------|--------|
| `_CONFIG_PATTERNS` | `config`, `settings`, `conf` |

### Template depths

| Constant | Values |
|----------|--------|
| `_DEPTH_NAMES` | `concept`, `task`, `reference` |

### File names

| Constant | Value |
|----------|-------|
| `_FEEDBACK_FILE` | `feedback.json` |
| `_MANIFEST_FILENAME` | `features.yaml` |

### Compound prefixes

| Constant | Values |
|----------|--------|
| `_COMPOUND_PREFIXES` | `ref-skill-`, `ref-tool-`, `ref-`, `tas-use-`, `tas-tool-`, `tas-`, `con-tool-`, `con-`, `err-`, `war-`, `tip-`, `faq-`, `not-`, `qui-`, `tro-`, `com-` |

### Excluded directories

| Constant | Values |
|----------|--------|
| `_EXCLUDED_DIRS` | `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules`, `.git` |
