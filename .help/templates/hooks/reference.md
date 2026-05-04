---
type: reference
feature: hooks
depth: reference
generated_at: 2026-05-04T02:43:32.097503+00:00
source_hash: ee7c91a1c6d86f5cfe8cb471894be8631647c9e853782d701bb219ccfe3deaf4
status: generated
---

# Hooks reference

Configure and execute custom actions that respond to events in the Attune AI lifecycle.

## Classes

| Class | Description |
|-------|-------------|
| `HookEvent` | Hook event types matching Claude Code lifecycle |
| `HookType` | Type of hook action |
| `HookDefinition` | Definition of a single hook action |
| `HookMatcher` | Matcher for determining when a hook should fire |
| `HookRule` | A complete hook rule with matcher and actions |
| `HookConfig` | Complete hook configuration for an Empathy session |
| `HookExecutor` | Executor for running hook actions |
| `HookExecutorSync` | Synchronous wrapper for HookExecutor |
| `HookRegistry` | Central registry for hook management and dispatch |

## Methods

### HookMatcher

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `matches` | `context: dict[str, Any]` | `bool` | Determines if the matcher conditions are met |

### HookConfig

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_hooks_for_event` | `event: HookEvent` | `list[HookRule]` | Retrieves all hook rules for a specific event |
| `add_hook` | `event: HookEvent, hook: HookDefinition, matcher: HookMatcher \| None = None, priority: int = 0` | `None` | Adds a new hook rule to the configuration |
| `from_yaml` | `yaml_path: str` | `HookConfig` | Creates a HookConfig from a YAML file |
| `to_yaml` | `yaml_path: str` | `None` | Saves the configuration to a YAML file |

### HookExecutor

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `python_handlers: dict[str, Callable] \| None = None` | | Initialize with optional Python handlers |
| `execute` | `hook: HookDefinition, context: dict[str, Any]` | `dict[str, Any]` | Execute a hook action with given context |

### HookExecutorSync

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `python_handlers: dict[str, Callable] \| None = None` | | Initialize synchronous wrapper with optional Python handlers |
| `execute` | `hook: HookDefinition, context: dict[str, Any]` | `dict[str, Any]` | Execute a hook action synchronously |

### HookRegistry

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: HookConfig \| None = None` | | Initialize registry with optional configuration |
| `load_config` | `config: HookConfig` | `None` | Load a hook configuration |
| `register` | `event: HookEvent, handler: Callable[..., Any], description: str = '', matcher: HookMatcher \| None = None, priority: int = 0` | `str` | Register a handler for an event |
| `unregister` | `handler_id: str` | `bool` | Unregister a handler by ID |
| `get_matching_hooks` | `event: HookEvent, context: dict[str, Any]` | `list[tuple[HookRule, HookDefinition]]` | Get all hooks that match the event and context |
| `fire` | `event: HookEvent, context: dict[str, Any] \| None = None` | `list[dict[str, Any]]` | Fire all matching hooks for an event |
| `fire_sync` | `event: HookEvent, context: dict[str, Any] \| None = None` | `list[dict[str, Any]]` | Fire all matching hooks synchronously |
| `get_execution_log` | `limit: int = 100, event_filter: HookEvent \| None = None` | `list[dict[str, Any]]` | Get execution log entries |
| `clear_execution_log` | | `None` | Clear the execution log |
| `get_stats` | | `dict[str, Any]` | Get registry statistics |

## Functions

### Session Evaluation

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_evaluate_session` | `context: dict[str, Any]` | `dict[str, Any]` | Evaluate a session for learning potential |
| `get_learning_summary` | `context: dict[str, Any]` | `dict[str, Any]` | Get learning summary for a user |
| `apply_learned_patterns` | `context: dict[str, Any]` | `str` | Generate context injection from learned patterns |

### Project Initialization

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_project_root` | `**context: Any` | `Path` | Get the project root directory |
| `is_initialized` | `project_root: Path` | `bool` | Check if Attune AI is initialized in the project |
| `get_never_ask_file` | `project_root: Path` | `Path` | Get path to the 'never ask' marker file |
| `should_skip_init` | `project_root: Path` | `bool` | Check if user previously said 'never ask again' |
| `mark_never_ask` | `project_root: Path` | `None` | Mark project to never ask about init again |
| `initialize_project` | `project_root: Path` | `dict[str, Any]` | Initialize Attune AI in the project |
| `check_init` | `**context: Any` | `dict[str, Any]` | Check if initialization is needed and return appropriate response |

### Compaction

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_pre_compact` | `context: dict[str, Any]` | `dict[str, Any]` | Execute pre-compaction state preservation |
| `suggest_compact` | `context: dict[str, Any]` | `dict[str, Any]` | Suggest compact when context grows too large |

## Constants

| Constant | Values | Description |
|----------|---------|-------------|
| `__all__` | `{'HookConfig', 'HookDefinition', 'HookEvent', 'HookExecutor', 'HookRegistry'}` | Exported hook classes |
| `__all__` | `{'apply_learned_patterns', 'check_init', 'get_learning_summary', 'handle_init_response', 'initialize_project', 'run_evaluate_session', 'run_pre_compact', 'suggest_compact'}` | Exported hook functions |
| `DEFAULT_CONFIG` | `'# Attune AI Configuration\n# Generated: {timestamp}\n\nagent:\n  name: empathy-assistant\n  model_tier: capable\n  empathy_level: 3\n\nhooks:\n  enabled: true\n  log_executions: false\n\nlearning:\n  enabled: true\n  auto_evaluate: true\n  quality_threshold: good\n  max_patterns_per_session: 10\n\ncontext:\n  auto_compact: true\n  token_threshold: 80\n'` | Default configuration template for new projects |
| `INIT_DIRECTORIES` | `{'.attune', '.attune/compact_states', '.attune/learned_skills', '.attune/sessions', '.attune/patterns'}` | Directories created during project initialization |
| `EXPECTED_KINDS` | `{'concept', 'task', 'reference', 'error', 'warning', 'troubleshooting', 'faq', 'quickstart', 'tip', 'note', 'comparison'}` | Valid template types |
| `SYSTEM_DIRECTORIES` | `{'/etc', '/sys', '/proc', '/dev', '/boot', '/sbin', '/usr/sbin', '/private/etc', '/private/var'}` | Protected system directories |
| `SEARCH_COMMAND_PREFIXES` | `{'grep', 'rg', 'ack', 'ag', 'git grep', 'git log', 'git diff'}` | Recognized search command prefixes |
