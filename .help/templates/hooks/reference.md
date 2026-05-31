---
feature: hooks
depth: reference
generated_at: 2026-05-31T14:15:05.561207+00:00
source_hash: 42b6f3d8928cb9d9f896c40c595715ed3473820bfdc5f12e14e2889aea7c4d0a
status: generated
---

# Hooks reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `HookEvent` | Hook event types matching Claude Code lifecycle. | `src/attune/hooks/config.py` |
| `HookType` | Type of hook action. | `src/attune/hooks/config.py` |
| `HookDefinition` | Definition of a single hook action. | `src/attune/hooks/config.py` |
| `HookMatcher` | Matcher for determining when a hook should fire. | `src/attune/hooks/config.py` |
| `HookRule` | A complete hook rule with matcher and actions. | `src/attune/hooks/config.py` |
| `HookConfig` | Complete hook configuration for an Empathy session. | `src/attune/hooks/config.py` |
| `HookExecutor` | Executor for running hook actions. | `src/attune/hooks/executor.py` |
| `HookExecutorSync` | Synchronous wrapper for HookExecutor. | `src/attune/hooks/executor.py` |
| `HookRegistry` | Central registry for hook management and dispatch. | `src/attune/hooks/registry.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `run_evaluate_session()` | Evaluate a session for learning potential. | `src/attune/hooks/scripts/evaluate_session.py` |
| `get_learning_summary()` | Get learning summary for a user. | `src/attune/hooks/scripts/evaluate_session.py` |
| `apply_learned_patterns()` | Generate context injection from learned patterns. | `src/attune/hooks/scripts/evaluate_session.py` |
| `get_project_root()` | Get the project root directory. | `src/attune/hooks/scripts/first_time_init.py` |
| `is_initialized()` | Check if Attune AI is initialized in the project. | `src/attune/hooks/scripts/first_time_init.py` |
| `get_never_ask_file()` | Get path to the 'never ask' marker file. | `src/attune/hooks/scripts/first_time_init.py` |
| `should_skip_init()` | Check if user previously said 'never ask again'. | `src/attune/hooks/scripts/first_time_init.py` |
| `mark_never_ask()` | Mark project to never ask about init again. | `src/attune/hooks/scripts/first_time_init.py` |
| `initialize_project()` | Initialize Attune AI in the project. | `src/attune/hooks/scripts/first_time_init.py` |
| `check_init()` | Check if initialization is needed and return appropriate response. | `src/attune/hooks/scripts/first_time_init.py` |
| `handle_init_response()` | Handle user's response to the initialization prompt. | `src/attune/hooks/scripts/first_time_init.py` |
| `main()` | Main hook entry point. | `src/attune/hooks/scripts/first_time_init.py` |
| `main()` | Read tool result from stdin, format Python files. | `src/attune/hooks/scripts/format_on_save.py` |
| `main()` | — | `src/attune/hooks/scripts/help_freshness_nudge.py` |
| `already_reminded()` | Return True if the reminder already fired within this session. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `mark_reminded()` | Write the sentinel file to suppress repeat reminders. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `has_session_work()` | Return True if this session produced git commits or file edits. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `main()` | Check if a lessons reminder should be shown and print it. | `src/attune/hooks/scripts/lessons_reminder.py` |
| `run_pre_compact()` | Execute pre-compaction state preservation. | `src/attune/hooks/scripts/pre_compact.py` |
| `generate_compaction_summary()` | Generate a summary suitable for including in compacted context. | `src/attune/hooks/scripts/pre_compact.py` |
| `validate_bash_command()` | Validate a Bash command against security policies. | `src/attune/hooks/scripts/security_guard.py` |
| `validate_file_path()` | Validate a file path against security policies. | `src/attune/hooks/scripts/security_guard.py` |
| `main()` | Validate a tool call against security policies. | `src/attune/hooks/scripts/security_guard.py` |
| `main()` | Print the starter-prompt notice if the file exists. | `src/attune/hooks/scripts/starter_prompt_nudge.py` |
| `get_compaction_state_file()` | Get the compaction state file path. | `src/attune/hooks/scripts/suggest_compact.py` |
| `load_compaction_state()` | Load compaction tracking state. | `src/attune/hooks/scripts/suggest_compact.py` |
| `save_compaction_state()` | Save compaction tracking state. | `src/attune/hooks/scripts/suggest_compact.py` |
| `should_suggest_compaction()` | Determine if compaction should be suggested. | `src/attune/hooks/scripts/suggest_compact.py` |
| `get_compaction_recommendations()` | Get recommendations for what to compact. | `src/attune/hooks/scripts/suggest_compact.py` |
| `main()` | Suggest compact hook main function. | `src/attune/hooks/scripts/suggest_compact.py` |
| `reset_on_compaction()` | Reset compaction state after a compaction event. | `src/attune/hooks/scripts/suggest_compact.py` |
| `record_telemetry()` | Record tool usage telemetry. | `src/attune/hooks/scripts/telemetry_hook.py` |


## Source files

- `src/attune/hooks/**`

## Tags

`hooks`, `webhooks`, `events`, `automation`
