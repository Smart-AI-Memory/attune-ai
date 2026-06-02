---
type: cli-reference
name: hooks
tags: [hooks, events, executor, registry, scripts]
source: src/attune/hooks/__init__.py
---

# Hooks CLI reference

## Description

The `hooks` command exposes the Attune AI hook system from the command line. It operates on hook events that fire at Claude Code lifecycle points (pre-tool, post-tool, and related triggers) and dispatches registered handlers through `HookRegistry`. Scripts bundled under `hooks` handle concrete concerns such as session evaluation, compaction, security validation, and telemetry recording.

## Usage

```
hooks [OPTIONS] SUBCOMMAND [ARGS]
```

## Subcommands

### Session evaluation

| Subcommand | Description |
|---|---|
| `run-evaluate-session` | Evaluates a session for learning potential. Accepts a `context` dict; returns a result dict. |
| `get-learning-summary` | Returns a learning summary dict for the current user context. |
| `apply-learned-patterns` | Generates a context-injection string from learned patterns. |

### Project initialization

| Subcommand | Description |
|---|---|
| `check-init` | Checks whether Attune AI is initialized in the project and returns the appropriate response dict. |
| `initialize-project` | Initializes Attune AI in the project root, creating `.attune` subdirectories. |
| `handle-init-response` | Handles the user's response (`action`) to the initialization prompt. |
| `should-skip-init` | Returns whether the user previously opted out of initialization prompts. |
| `mark-never-ask` | Writes the never-ask marker file to suppress future initialization prompts. |
| `get-never-ask-file` | Prints the path to the never-ask marker file for the given project root. |
| `get-project-root` | Resolves and prints the project root directory. |
| `is-initialized` | Exits `0` if Attune AI is initialized in the given project root, `1` otherwise. |

### Compaction

| Subcommand | Description |
|---|---|
| `run-pre-compact` | Executes pre-compaction state preservation. Accepts a `context` dict. |
| `generate-compaction-summary` | Generates a compaction summary string suitable for inclusion in compacted context. |
| `should-suggest-compaction` | Determines whether compaction should be suggested based on state, threshold, and interval. |
| `get-compaction-recommendations` | Returns a list of compaction recommendations for the given context. |
| `suggest-compact` | Main suggest-compact hook entry point. |
| `reset-on-compaction` | Resets compaction tracking state after a compaction event. |
| `get-compaction-state-file` | Prints the path to the compaction state file. |
| `load-compaction-state` | Loads and prints the compaction tracking state. |
| `save-compaction-state` | Persists updated compaction tracking state. |

### Security

| Subcommand | Description |
|---|---|
| `validate-bash-command` | Validates a Bash command string against security policies. Returns a `(allowed, reason)` tuple. |
| `validate-file-path` | Validates a file path against security policies. Returns a `(allowed, reason)` tuple. |
| `security-guard` | Validates a tool call against security policies using the full `context` dict. |
| `worktree-path-guard` | Validates that the target path matches the current session's worktree. |

### Notifications and telemetry

| Subcommand | Description |
|---|---|
| `lessons-reminder` | Checks whether a lessons reminder should be shown and prints it if so. |
| `already-reminded` | Exits `0` if the session-scoped reminder sentinel file exists. |
| `mark-reminded` | Writes the sentinel file to suppress repeat reminders within the session. |
| `has-session-work` | Exits `0` if this session produced git commits or file edits. |
| `starter-prompt-nudge` | Prints the starter-prompt notice if the trigger file exists. |
| `help-freshness-nudge` | Prints a help-freshness notice when appropriate. |
| `record-telemetry` | Records tool-usage telemetry for the given context. |
| `format-on-save` | Reads a tool result from stdin and formats Python files referenced in it. |

## Options

| Option | Description |
|--------|-------------|
| `--help` | Show help text and exit. |

## Output

Subcommands that return structured data emit a JSON dict to stdout. Example output from `run-evaluate-session`:

```json
{
  "evaluated": true,
  "quality": "good",
  "patterns_found": 3,
  "session_id": "ses_20260602_abcdef"
}
```

Subcommands that perform a single check (for example, `is-initialized`, `already-reminded`, `has-session-work`) produce no stdout output; their result is communicated through the exit code.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success, or the checked condition is true. |
| `1` | Failure, or the checked condition is false (for boolean-check subcommands). |

## Related commands

- `attune registry` — inspect and manage the `HookRegistry` directly
- `attune config` — load or export `HookConfig` from a YAML file via `from_yaml` / `to_yaml`
- `attune compact` — trigger compaction manually; fires the hooks handled by `run-pre-compact` and `reset-on-compaction`

<!-- attune-generated: source_hash=4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9 feature=hooks kind=cli-reference generated_at=2026-06-02 -->
