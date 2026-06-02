---
type: reference
name: hooks-reference
feature: hooks
depth: reference
generated_at: 2026-06-02T10:56:02.699014+00:00
source_hash: 4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9
status: generated
---

# Hooks reference

Use the hooks API to register, configure, and fire lifecycle hooks tied to Claude Code events. The public surface exported from `hooks` covers configuration models, execution, and registry management. Hook scripts under `scripts` provide ready-made handlers for common lifecycle tasks.

## Classes

| Class | Description |
|-------|-------------|
| `HookEvent` | Hook event types matching Claude Code lifecycle. |
| `HookType` | Type of hook action. |
| `HookDefinition` | Definition of a single hook action. |
| `HookMatcher` | Determines whether a hook fires for a given context. |
| `HookRule` | A complete hook rule combining a matcher with one or more actions. |
| `HookConfig` | Complete hook configuration for an Empathy session. |
| `HookExecutor` | Runs hook actions, with support for Python handlers. |
| `HookExecutorSync` | Synchronous wrapper for `HookExecutor`. |
| `HookRegistry` | Central registry for hook management and dispatch. |

---

### `HookMatcher`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `matches` | `context: dict[str, Any]` | `bool` | Returns `True` when the hook should fire for the given context. |

---

### `HookConfig`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_hooks_for_event` | `event: HookEvent` | `list[HookRule]` | Returns all rules registered for the given event. |
| `add_hook` | `event: HookEvent, hook: HookDefinition, matcher: HookMatcher \| None = None, priority: int = 0` | `None` | Registers a hook definition for an event, with optional matcher and priority. |
| `from_yaml` | `yaml_path: str` | `'HookConfig'` | Loads a `HookConfig` from a YAML file at the given path. |
| `to_yaml` | `yaml_path: str` | `None` | Writes the current configuration to a YAML file at the given path. |

---

### `HookExecutor`

#### Constructor

| Parameters | Description |
|------------|-------------|
| `python_handlers: dict[str, Callable] \| None = None` | Optional mapping of handler names to callables, used when executing Python-type hooks. |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `hook: HookDefinition, context: dict[str, Any]` | `dict[str, Any]` | Runs the given hook action against the provided context and returns the result. |

---

### `HookExecutorSync`

#### Constructor

| Parameters | Description |
|------------|-------------|
| `python_handlers: dict[str, Callable] \| None = None` | Optional mapping of handler names to callables. |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `hook: HookDefinition, context: dict[str, Any]` | `dict[str, Any]` | Synchronously runs the given hook action and returns the result. |

---

### `HookRegistry`

#### Constructor

| Parameters | Description |
|------------|-------------|
| `config: HookConfig \| None = None` | Optional initial configuration to load into the registry. |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `load_config` | `config: HookConfig` | `None` | Loads a `HookConfig`, replacing any previously registered config-derived hooks. |
| `register` | `event: HookEvent, handler: Callable[..., Any], description: str = '', matcher: HookMatcher \| None = None, priority: int = 0` | `str` | Registers a callable handler for an event and returns its assigned handler ID. |
| `unregister` | `handler_id: str` | `bool` | Removes the handler with the given ID. Returns `True` if the handler was found and removed. |
| `get_matching_hooks` | `event: HookEvent, context: dict[str, Any]` | `list[tuple[HookRule, HookDefinition]]` | Returns all rules and definitions whose matchers pass for the given event and context. |
| `fire` | `event: HookEvent, context: dict[str, Any] \| None = None` | `list[dict[str, Any]]` | Fires all matching hooks for the event and returns their results. |
| `fire_sync` | `event: HookEvent, context: dict[str, Any] \| None = None` | `list[dict[str, Any]]` | Synchronously fires all matching hooks for the event and returns their results. |
| `get_execution_log` | `limit: int = 100, event_filter: HookEvent \| None = None` | `list[dict[str, Any]]` | Returns up to `limit` recent execution log entries, optionally filtered by event type. |
| `clear_execution_log` | — | `None` | Clears all entries from the execution log. |
| `get_stats` | — | `dict[str, Any]` | Returns execution statistics for the registry. |

---

## Script functions

These functions are the ready-made hook handlers exported from `scripts`.

### Session evaluation (`scripts.evaluate_session`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_evaluate_session` | `context: dict[str, Any]` | `dict[str, Any]` | Evaluates a session for learning potential. |
| `get_learning_summary` | `context: dict[str, Any]` | `dict[str, Any]` | Returns a learning summary for the session. |
| `apply_learned_patterns` | `context: dict[str, Any]` | `str` | Generates context injection text from learned patterns. |

### Project initialization (`scripts.first_time_init`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_project_root` | `**context: Any` | `Path` | Returns the project root directory. |
| `is_initialized` | `project_root: Path` | `bool` | Returns `True` if Attune AI is already initialized in the project. |
| `get_never_ask_file` | `project_root: Path` | `Path` | Returns the path to the "never ask" marker file. |
| `should_skip_init` | `project_root: Path` | `bool` | Returns `True` if the user previously chose "never ask again". |
| `mark_never_ask` | `project_root: Path` | `None` | Writes the "never ask" marker file for the project. |
| `initialize_project` | `project_root: Path` | `dict[str, Any]` | Initializes Attune AI in the project directory. |
| `check_init` | `**context: Any` | `dict[str, Any]` | Checks whether initialization is needed and returns the appropriate response. |
| `handle_init_response` | `action: str, **context: Any` | `dict[str, Any]` | Handles the user's response to the initialization prompt. |
| `main` | `**context: Any` | `dict[str, Any]` | Hook entry point for first-time initialization. |

### Format on save (`scripts.format_on_save`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `None` | Reads the tool result from stdin and formats Python files. |

### Help freshness nudge (`scripts.help_freshness_nudge`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Hook entry point for the help freshness nudge. |

### Lessons reminder (`scripts.lessons_reminder`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `already_reminded` | — | `bool` | Returns `True` if the reminder has already fired within this session. |
| `mark_reminded` | — | `None` | Writes the sentinel file to suppress repeat reminders. |
| `has_session_work` | — | `bool` | Returns `True` if this session produced git commits or file edits. |
| `main` | — | `int` | Checks whether a lessons reminder should be shown and prints it. |

### Pre-compaction (`scripts.pre_compact`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_pre_compact` | `context: dict[str, Any]` | `dict[str, Any]` | Executes pre-compaction state preservation. |
| `generate_compaction_summary` | `collaboration_state: Any, include_patterns: bool = True, include_history: bool = False` | `str` | Generates a summary suitable for inclusion in compacted context. |

### Security guard (`scripts.security_guard`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Validates a Bash command against security policies. |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Validates a file path against security policies. |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validates a tool call against security policies. |

### Starter prompt nudge (`scripts.starter_prompt_nudge`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | — | `int` | Prints the starter-prompt notice if the file exists. |

### Compaction suggestions (`scripts.suggest_compact`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_compaction_state_file` | — | `Path` | Returns the path to the compaction state file. |
| `load_compaction_state` | — | `dict[str, Any]` | Loads compaction tracking state from disk. |
| `save_compaction_state` | `state: dict[str, Any]` | `None` | Saves compaction tracking state to disk. |
| `should_suggest_compaction` | `state: dict[str, Any], threshold: int = DEFAULT_COMPACT_THRESHOLD, interval: int = DEFAULT_REMINDER_INTERVAL` | `tuple[bool, str]` | Returns whether compaction should be suggested and an explanatory message. |
| `get_compaction_recommendations` | `context: dict[str, Any]` | `list[str]` | Returns a list of recommendations for what to compact. |
| `main` | `**context: Any` | `dict[str, Any]` | Hook entry point for compaction suggestions. |
| `reset_on_compaction` | `**context: Any` | `dict[str, Any]` | Resets compaction tracking state after a compaction event. |

### Telemetry (`scripts.telemetry_hook`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `record_telemetry` | `context: dict[str, Any]` | `None` | Records tool usage telemetry from the hook context. |

### Worktree path guard (`scripts.worktree_path_guard`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | `context: dict[str, Any]` | `int` | Validates that the target path matches the session's worktree. |

---

## Source files

- `src/attune/hooks/**`

## Tags

`hooks`, `webhooks`, `events`, `automation`
