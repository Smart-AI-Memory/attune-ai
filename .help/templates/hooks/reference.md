---
type: reference
name: hooks-reference
feature: hooks
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 92f76c4d4d77b21e59b9a6aed8e65dd221371f5ce10f2941171a5c0310c232c1
status: generated
scaffold_hash: ecf92cd0a9d28d4a09669183241ef08059389f8bc15e663ad79a0e6b7e8362fa
---

# Hooks reference

Use the hooks API to attach custom behavior to Claude Code lifecycle events. You can define hooks declaratively in YAML via `HookConfig`, or register Python callable handlers programmatically through `HookRegistry`, then fire them synchronously or asynchronously against a runtime context dict. The `hooks.scripts` package ships ready-to-use scripts for security validation, context compaction, session learning, telemetry recording, and first-time project setup.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `HookEvent` | Hook event types matching Claude Code lifecycle. | `src/attune/hooks/config.py` |
| `HookType` | Type of hook action. | `src/attune/hooks/config.py` |
| `HookDefinition` | Definition of a single hook action. | `src/attune/hooks/config.py` |
| `HookMatcher` | Evaluates context to decide whether a hook should fire. | `src/attune/hooks/config.py` |
| `HookRule` | A complete hook rule with a matcher and its associated actions. | `src/attune/hooks/config.py` |
| `HookConfig` | Complete hook configuration for an Empathy session. | `src/attune/hooks/config.py` |
| `HookExecutor` | Runs hook actions asynchronously. | `src/attune/hooks/executor.py` |
| `HookExecutorSync` | Synchronous wrapper for `HookExecutor`. | `src/attune/hooks/executor.py` |
| `HookRegistry` | Central registry for hook management and dispatch. | `src/attune/hooks/registry.py` |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `is_sdk_subprocess` | — | `bool` | Returns `True` when running inside an SDK-spawned `claude` subprocess. | `src/attune/hooks/scripts/_sdk_gate.py` |
| `exit_if_sdk_subprocess` | — | `None` | Exits with code 0 and produces no output when inside an SDK subprocess session. | `src/attune/hooks/scripts/_sdk_gate.py` |
| `run_evaluate_session` | `context: dict[str, Any]` | `dict[str, Any]` | Evaluates a session for learning potential. | `src/attune/hooks/scripts/evaluate_session.py` |
| `get_learning_summary` | `context: dict[str, Any]` | `dict[str, Any]` | Returns the learning summary for the current user. | `src/attune/hooks/scripts/evaluate_session.py` |
| `apply_learned_patterns` | `context: dict[str, Any]` | `str` | Generates a context-injection string from learned patterns. | `src/attune/hooks/scripts/evaluate_session.py` |
| `get_project_root` | `**context: Any` | `Path` | Returns the project root directory. | `src/attune/hooks/scripts/first_time_init.py` |
| `is_initialized` | `project_root: Path` | `bool` | Returns `True` if Attune AI is initialized in the given project root. | `src/attune/hooks/scripts/first_time_init.py` |
| `get_never_ask_file` | `project_root: Path` | `Path` | Returns the path to the 'never ask again' marker file. | `src/attune/hooks/scripts/first_time_init.py` |
| `should_skip_init` | `project_root: Path` | `bool` | Returns `True` if the user previously chose 'never ask again'. | `src/attune/hooks/scripts/first_time_init.py` |
| `mark_never_ask` | `project_root: Path` | `None` | Writes the 'never ask again' marker to suppress future init prompts. | `src/attune/hooks/scripts/first_time_init.py` |
| `initialize_project` | `project_root: Path` | `dict[str, Any]` | Sets up the Attune AI directory structure under the project root. | `src/attune/hooks/scripts/first_time_init.py` |
| `check_init` | `**context: Any` | `dict[str, Any]` | Returns an initialization prompt if Attune AI is not yet set up in the project. | `src/attune/hooks/scripts/first_time_init.py` |
| `handle_init_response` | `action: str, **context: Any` | `dict[str, Any]` | Processes the user's response to the initialization prompt. | `src/attune/hooks/scripts/first_time_init.py` |
| `main` | `**context: Any` | `dict[str, Any]` | Entry point for the first-time initialization hook. | `src/attune/hooks/scripts/first_time_init.py` |
| `main` | — | `None` | Reads a tool result from stdin and formats Python files. | `src/attune/hooks/scripts/format_on_save.py` |
| `main` | — | `int` | — | `src/attune/hooks/scripts/help_freshness_nudge.py` |
| `already_reminded` | — | `bool` | Returns `True` if the lessons reminder already fired in this session. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `mark_reminded` | — | `None` | Writes the sentinel file to prevent repeat reminders in this session. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `has_session_work` | — | `bool` | Returns `True` if this session produced git commits or file edits. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `main` | — | `int` | Checks whether to print a lessons reminder and prints it. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `run_pre_compact` | `context: dict[str, Any]` | `dict[str, Any]` | Saves collaboration state before context compaction. | `src/attune/hooks/scripts/pre_compact.py` |
| `generate_compaction_summary` | `collaboration_state: Any, include_patterns: bool = True, include_history: bool = False` | `str` | Generates a summary string for inclusion in the compacted context. | `src/attune/hooks/scripts/pre_compact.py` |
| `validate_bash_command` | `command: str` | `tuple[bool, str]` | Checks a Bash command against security policies; returns `(valid, message)`. | `src/attune/hooks/scripts/security_guard.py` |
| `validate_file_path` | `file_path: str` | `tuple[bool, str]` | Checks a file path against security policies; returns `(valid, message)`. | `src/attune/hooks/scripts/security_guard.py` |
| `main` | `context: dict[str, Any]` | `dict[str, Any]` | Validates a tool call against security policies and returns a decision dict. | `src/attune/hooks/scripts/security_guard.py` |
| `main` | — | `int` | Prints the starter-prompt notice if the file exists. | `src/attune/hooks/scripts/starter_prompt_nudge.py` |
| `get_compaction_state_file` | — | `Path` | Returns the path to the compaction tracking state file. | `src/attune/hooks/scripts/suggest_compact.py` |
| `load_compaction_state` | — | `dict[str, Any]` | Loads compaction tracking state from disk. | `src/attune/hooks/scripts/suggest_compact.py` |
| `save_compaction_state` | `state: dict[str, Any]` | `None` | Writes compaction tracking state to disk. | `src/attune/hooks/scripts/suggest_compact.py` |
| `should_suggest_compaction` | `state: dict[str, Any], threshold: int = DEFAULT_COMPACT_THRESHOLD, interval: int = DEFAULT_REMINDER_INTERVAL` | `tuple[bool, str]` | Returns `(True, reason)` when compaction should be suggested, `(False, '')` otherwise. | `src/attune/hooks/scripts/suggest_compact.py` |
| `get_compaction_recommendations` | `context: dict[str, Any]` | `list[str]` | Returns a list of compaction recommendations based on the current context. | `src/attune/hooks/scripts/suggest_compact.py` |
| `main` | `**context: Any` | `dict[str, Any]` | Entry point for the suggest-compact hook. | `src/attune/hooks/scripts/suggest_compact.py` |
| `reset_on_compaction` | `**context: Any` | `dict[str, Any]` | Resets compaction tracking state after a compaction event. | `src/attune/hooks/scripts/suggest_compact.py` |
| `record_telemetry` | `context: dict[str, Any]` | `None` | Records tool usage telemetry from the hook context. | `src/attune/hooks/scripts/telemetry_hook.py` |
| `main` | `context: dict[str, Any]` | `int` | Validates the target path against the session's worktree; exits non-zero on mismatch. | `src/attune/hooks/scripts/worktree_path_guard.py` |

## Constants

| Constant | Type | Members / Value | Description |
|----------|------|-----------------|-------------|
| `DEFAULT_CONFIG` | `str` | See below | Default YAML template written to disk during project initialization. |
| `ENFORCEMENT_NAME` | `str` | `'worktree_path_guard'` | Name identifier used by the worktree path guard script. |
| `EXPECTED_KINDS` | `set` | `'concept'`, `'task'`, `'reference'`, `'error'`, `'warning'`, `'troubleshooting'`, `'faq'`, `'quickstart'`, `'tip'`, `'note'`, `'comparison'` | Allowed help-content kind identifiers. |
| `INIT_DIRECTORIES` | `list` | `'.attune'`, `'.attune/compact_states'`, `'.attune/learned_skills'`, `'.attune/sessions'`, `'.attune/patterns'` | Directories created under the project root during initialization. |
| `SEARCH_COMMAND_PREFIXES` | `frozenset` | `'grep'`, `'rg'`, `'ack'`, `'ag'`, `'git grep'`, `'git log'`, `'git diff'` | Shell command prefixes the security guard treats as read-only searches. |
| `SYSTEM_DIRECTORIES` | `frozenset` | `'/etc'`, `'/sys'`, `'/proc'`, `'/dev'`, `'/boot'`, `'/sbin'`, `'/usr/sbin'`, `'/private/etc'`, `'/private/var'` | System paths the security guard blocks from file writes. |

### `DEFAULT_CONFIG`

```yaml
# Attune AI Configuration
# Generated: {timestamp}

agent:
  name: empathy-assistant
  model_tier: capable
  empathy_level: 3

hooks:
  enabled: true
  log_executions: false

learning:
  enabled: true
  auto_evaluate: true
  quality_threshold: good
  max_patterns_per_session: 10

context:
  auto_compact: true
  token_threshold: 80
```

## Source files

- `src/attune/hooks/**`

## Tags

`hooks`, `webhooks`, `events`, `automation`
