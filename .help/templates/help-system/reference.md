---
type: reference
name: help-system-reference
feature: help-system
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 15713124af0cd76c022a741b771c19b44c22f9a2907b20d728e874c8b91b68f5
status: generated
---

# Help System reference

APIs for building, populating, maintaining, and rendering progressive-depth help templates.

## Classes

| Class | Description |
|-------|-------------|
| `ProposedFeature` | A feature discovered by scanning. |
| `GeneratedTemplate` | Result of generating one template file. |
| `GenerationResult` | Result of generating templates for a feature. |
| `MaintenanceResult` | Result of a help maintenance run. |
| `Feature` | A project feature mapped to source files. |
| `FeatureManifest` | Parsed features.yaml manifest. |
| `FeatureStaleness` | Staleness status for one feature. |
| `StalenessReport` | Staleness report across all features. |
| `TemplateContext` | Runtime parameters for template population. |
| `AudienceProfile` | Target audience for output adaptation. |
| `PopulatedTemplate` | Result of template population. |

### `ProposedFeature` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `files` | `list[str]` | `field(default_factory=list)` |
| `tags` | `list[str]` | `field(default_factory=list)` |
| `confidence` | `str` | `'medium'` |
| `reason` | `str` | `''` |

### `GeneratedTemplate` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `feature` | `str` | — |
| `depth` | `str` | — |
| `path` | `Path` | — |
| `source_hash` | `str` | — |

### `GenerationResult` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `feature` | `str` | — |
| `templates` | `list[GeneratedTemplate]` | `field(default_factory=list, compare=False)` |
| `source_hash` | `str` | `field(default='', compare=False)` |
| `matched_files` | `list[str]` | `field(default_factory=list, compare=False)` |

### `MaintenanceResult` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `staleness` | `StalenessReport` | — |
| `regenerated` | `list[GenerationResult]` | `field(default_factory=list)` |
| `skipped_manual` | `list[str]` | `field(default_factory=list)` |
| `failed` | `list[str]` | `field(default_factory=list)` |

#### `MaintenanceResult` properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Number of stale features detected. |
| `regenerated_count` | `int` | Number of features regenerated. |

### `Feature` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `files` | `list[str]` | `field(default_factory=list)` |
| `tags` | `list[str]` | `field(default_factory=list)` |

### `FeatureManifest` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `version` | `int` | — |
| `features` | `dict[str, Feature]` | — |
| `path` | `Path | None` | `None` |

### `FeatureStaleness` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `feature` | `str` | — |
| `is_stale` | `bool` | — |
| `current_hash` | `str` | — |
| `stored_hash` | `str | None` | — |
| `matched_files` | `list[str]` | `field(default_factory=list)` |

### `StalenessReport` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `entries` | `list[FeatureStaleness]` | — |

#### `StalenessReport` properties

| Property | Type | Description |
|----------|------|-------------|
| `stale_count` | `int` | Count of stale features. |
| `current_count` | `int` | Count of up-to-date features. |
| `stale_features` | `list[str]` | Names of stale features. |

### `TemplateContext` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `file_path` | `str | None` | `None` |
| `error_message` | `str | None` | `None` |
| `workflow_name` | `str | None` | `None` |
| `tool_name` | `str | None` | `None` |
| `skill_name` | `str | None` | `None` |
| `extra` | `dict[str, Any]` | `field(default_factory=dict)` |

### `AudienceProfile` fields

[dataclass]

| Field | Type | Default |
|-------|------|---------|
| `channel` | `str` | `'claude-code'` |
| `verbosity` | `str` | `'normal'` |

## Functions

### Bootstrap

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `scan_project` | `project_root: str \| Path` | `list[ProposedFeature]` | Scan a project and propose features. |
| `proposals_to_manifest` | `proposals: list[ProposedFeature]` | `FeatureManifest` | Convert accepted proposals to a FeatureManifest. |

### Feedback and discovery

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `record_template_feedback` | `template_id: str, rating: str, *, generated_dir: str \| Path \| None = None` | `float` | Record user feedback on a template. |
| `get_template_confidence` | `template_id: str, *, generated_dir: str \| Path \| None = None` | `float` | Get confidence score based on feedback. |
| `get_usage_weights` | `days: int = 30` | `dict[str, float]` | Get template relevance weights from usage telemetry. |
| `search_by_tag` | `tag: str, *, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `list[str]` | Find template IDs matching a tag. |
| `list_tags` | `*, generated_dir: str \| Path \| None = None, sort_by_usage: bool = False` | `dict[str, int]` | List all tags with their template counts. |
| `get_workflow_help` | `workflow_name: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get help templates relevant after a workflow completes. |
| `get_precursor_warnings` | `file_path: str, *, generated_dir: str \| Path \| None = None, max_results: int = 3` | `list[PopulatedTemplate]` | Get warnings relevant to a file being edited. |

### Generation

| Function | Parameters | Returns | Description | Raises |
|----------|------------|---------|-------------|--------|
| `generate_feature_templates` | `feature: Feature, help_dir: str \| Path, project_root: str \| Path, depths: list[str] \| None = None, overwrite: bool = False` | `GenerationResult` | Generate help templates for a feature. | `ValueError` — `'Invalid feature name: {...}'` |

### Maintenance

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_maintenance` | `help_dir: str \| Path, project_root: str \| Path, features: list[str] \| None = None, dry_run: bool = False` | `MaintenanceResult` | Check staleness and regenerate stale help templates. |
| `get_changed_files` | `project_root: str \| Path` | `list[str]` | Get files changed in the most recent commit. |
| `run_hook` | `help_dir: str \| Path, project_root: str \| Path` | `MaintenanceResult \| None` | Post-commit hook entry point. |
| `format_status_report` | `report: StalenessReport, help_dir: str \| Path \| None = None` | `str` | Format a staleness report for display. |

### Manifest

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_manifest` | `help_dir: str \| Path` | `FeatureManifest` | Load and validate features.yaml from a .help/ directory. |
| `save_manifest` | `manifest: FeatureManifest, help_dir: str \| Path` | `Path` | Write a FeatureManifest to features.yaml. |
| `match_files_to_features` | `changed_files: list[str], manifest: FeatureManifest` | `dict[str, list[str]]` | Match changed files against feature glob patterns. |
| `resolve_topic` | `query: str, manifest: FeatureManifest` | `str \| None` | Resolve a user query to a feature name. |

### Polish

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `polish_template` | `content: str, feature_name: str, source_summary: str` | `str` | Polish a generated template using an LLM. |
| `build_source_summary` | `public_classes: list[dict[str, str]], public_functions: list[dict[str, str]], module_docstrings: list[str], file_count: int` | `str` | Build a concise source summary for the polish prompt. |

### Preamble

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_preamble` | `feature_name: str, help_dir: str \| Path \| None = None` | `str \| None` | Get the one-liner preamble for a feature. |
| `get_related_preambles` | `feature_name: str, help_dir: str \| Path \| None = None, max_results: int = 3` | `list[dict[str, str]]` | Get preambles for features related by shared tags. |

### Progression

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `populate_progressive` | `template_id: str, context: Any = None, audience: AudienceProfile \| None = None, *, generated_dir: str \| Path \| None = None, starting_level: int \| None = None` | `PopulatedTemplate \| None` | Populate a template with type-driven depth escalation. |

### Session

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_state` | — | `dict[str, Any]` | Get the current session state (thread-safe read). |
| `update_state` | `topic: str, starting_level: int \| None = None` | `int` | Update session state for a topic access. |
| `reset_session` | — | `None` | Reset progressive depth to defaults. |

### Staleness

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `compute_source_hash` | `feature: Feature, project_root: str \| Path` | `tuple[str, list[str]]` | Compute SHA-256 hash of a feature's source files. |
| `check_staleness` | `manifest: FeatureManifest, help_dir: str \| Path, project_root: str \| Path, features: list[str] \| None = None` | `StalenessReport` | Check which features have stale help templates. |

### Templates

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `invalidate_cross_links_cache` | — | `None` | Clear the cross-links cache so the next lookup re-reads disk. |
| `populate` | `template_id: str, context: TemplateContext \| None = None, audience: AudienceProfile \| None = None, *, generated_dir: str \| Path \| None = None, compose: bool = False` | `PopulatedTemplate \| None` | Populate a template with context and audience adaptation. |

### Renderers

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `render_claude_code` | `template: PopulatedTemplate` | `str` | Render a template for inline Claude Code conversation. |
| `render_marketplace` | `template: PopulatedTemplate` | `str` | Render a template for agentskills.io documentation page. |
| `render_cli` | `template: PopulatedTemplate` | `str` | Render a template for terminal display via `attune help`. |

## Constants

| Constant | Type | Members |
|----------|------|---------|
| `_DEPTH_NAMES` | `tuple` | `'concept'`, `'task'`, `'reference'` |
| `_MANIFEST_FILENAME` | `str` | `'features.yaml'` |
| `_FEEDBACK_FILE` | `str` | `'feedback.json'` |
| `_SKIP_DIRS` | `set` | `'.git'`, `'.github'`, `'.help'`, `'.claude'`, `'.agents'`, `'__pycache__'`, `'.mypy_cache'`, `'.pytest_cache'`, `'.ruff_cache'`, `'.tox'`, `'.venv'`, `'venv'`, `'env'`, `'node_modules'`, `'dist'`, `'build'`, `'.egg-info'`, `'htmlcov'`, `'site'` |
| `_ENTRY_POINT_NAMES` | `set` | `'main.py'`, `'app.py'`, `'cli.py'`, `'server.py'`, `'manage.py'`, `'wsgi.py'`, `'asgi.py'`, `'index.ts'`, `'index.js'`, `'main.go'`, `'main.rs'` |
| `_CONFIG_PATTERNS` | `set` | `'config'`, `'settings'`, `'conf'` |
| `_EXCLUDED_DIRS` | `set` | `'__pycache__'`, `'.mypy_cache'`, `'.pytest_cache'`, `'.ruff_cache'`, `'node_modules'`, `'.git'` |
| `_COMPOUND_PREFIXES` | `list` | `'ref-skill-'`, `'ref-tool-'`, `'ref-'`, `'tas-use-'`, `'tas-tool-'`, `'tas-'`, `'con-tool-'`, `'con-'`, `'err-'`, `'war-'`, `'tip-'`, `'faq-'`, `'not-'`, `'qui-'`, `'tro-'`, `'com-'` |

## Source files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

## Tags

`help`, `templates`, `docs`
