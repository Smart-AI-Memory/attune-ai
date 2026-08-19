---
description: Hook System: The Attune AI hook system provides event-driven extensibility for session lifecycle management.
---

# Hook System

The Attune AI hook system provides event-driven extensibility for session lifecycle management.

## Overview

Hooks allow you to execute custom code at specific points in the session lifecycle:

- **SessionStart/SessionEnd**: Initialize or cleanup session state
- **PreToolUse/PostToolUse**: Intercept tool calls
- **PreCompact/PostCompact**: Handle context compaction
- **PreCommand/PostCommand**: Wrap command execution

## Quick Start

```python
from attune.hooks import HookRegistry, HookEvent

# Create registry
registry = HookRegistry()

# Register a hook
def on_session_start(context):
    print(f"Session started for user: {context.get('user_id')}")
    return {"success": True}

registry.register(
    event=HookEvent.SESSION_START,
    handler=on_session_start,
    description="Log session start"
)

# Fire the hook
results = registry.fire_sync(
    HookEvent.SESSION_START,
    context={"user_id": "user123"}
)
```

## Hook Events

| Event | When Fired | Typical Use Case |
|-------|------------|------------------|
| `SESSION_START` | Session begins | Restore state, initialize |
| `SESSION_END` | Session ends | Save state, cleanup |
| `PRE_TOOL_USE` | Before tool executes | Validation, logging |
| `POST_TOOL_USE` | After tool executes | Post-processing |
| `PRE_COMPACT` | Before compaction | Save critical state |
| `POST_COMPACT` | After compaction | Verify preservation |
| `PRE_COMMAND` | Before command runs | Setup, validation |
| `POST_COMMAND` | After command runs | Cleanup, logging |
| `STOP` | Session terminated | Emergency cleanup |

## Configuration

### YAML Configuration

```yaml
# hooks.yaml
hooks:
  SessionStart:
    - matcher:
        match_all: true
      hooks:
        - type: python
          command: attune.hooks.scripts.first_time_init:main
          description: Restore previous context

  PostToolUse:
    - matcher:
        tool: Edit
        file_pattern: "\\.py$"
      hooks:
        - type: command
          command: "ruff format {file_path}"
          description: Auto-format Python files

enabled: true
log_executions: true
```

### Loading Configuration

```python
from attune.hooks import HookConfig

config = HookConfig.from_yaml("hooks.yaml")
registry = HookRegistry(config=config)
```

## Hook Matchers

Matchers determine when hooks fire:

```python
from attune.hooks.config import HookMatcher

# Match specific tool
tool_matcher = HookMatcher(tool="Edit")

# Match file patterns
py_matcher = HookMatcher(file_pattern=r"\.py$")

# Match everything
wildcard = HookMatcher(match_all=True)

# Combined matching
combined = HookMatcher(
    tool="Edit",
    file_pattern=r"\.py$"
)
```

## Hook Types

### Python Hooks

```python
def my_handler(context: dict) -> dict:
    # Process context
    return {"success": True, "output": "processed"}

registry.register(
    event=HookEvent.SESSION_START,
    handler=my_handler,
)
```

### Command Hooks

Execute shell commands:

```yaml
hooks:
  PostToolUse:
    - hooks:
        - type: command
          command: "echo 'Tool used: {tool}'"
```

### Webhook Hooks

Call external APIs:

```yaml
hooks:
  SessionEnd:
    - hooks:
        - type: webhook
          command: "https://api.example.com/session-end"
```

## Priority and Order

Hooks execute in priority order (higher first):

```python
registry.register(
    event=HookEvent.SESSION_START,
    handler=high_priority_handler,
    priority=100,  # Runs first
)

registry.register(
    event=HookEvent.SESSION_START,
    handler=low_priority_handler,
    priority=0,  # Runs last
)
```

## Error Handling

Configure error behavior per hook:

```python
HookDefinition(
    type=HookType.PYTHON,
    command="handler",
    on_error="log",    # Log and continue (default)
    # on_error="raise", # Raise exception
    # on_error="ignore", # Silent ignore
)
```

## Execution Logging

Track hook executions:

```python
registry = HookRegistry(config=HookConfig(log_executions=True))

# After some hooks fire...
log = registry.get_execution_log(limit=10)
for entry in log:
    print(f"{entry['event']}: {entry['success']}")
```

## Statistics

```python
stats = registry.get_stats()
print(f"Total hooks: {stats['total_hooks']}")
print(f"Executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
```

## Built-in Hook Scripts

The framework includes pre-built hook scripts:

| Script | Event | Purpose |
|--------|-------|---------|
| `session_start.py` | SessionStart | Restore context state |
| `session_end.py` | SessionEnd | Save state, trigger evaluation |
| `suggest_compact.py` | PostToolUse | Suggest compaction when needed |
| `evaluate_session.py` | SessionEnd | Extract learning patterns |

## Integration with Commands

Commands can specify hooks in their metadata:

```yaml
---
name: compact
hooks:
  pre: PreCompact
  post: PostCompact
---
```

The `CommandExecutor` automatically fires these hooks:

```python
executor = CommandExecutor(context)
result = executor.execute(command)
# PreCompact fires before, PostCompact fires after
```

## API Reference

### HookRegistry

```python
class HookRegistry:
    def register(event, handler, description="", matcher=None, priority=0) -> str
    def unregister(handler_id) -> bool
    def fire(event, context=None) -> list[dict]  # async
    def fire_sync(event, context=None) -> list[dict]
    def get_matching_hooks(event, context) -> list[tuple]
    def get_execution_log(limit=100, event_filter=None) -> list[dict]
    def get_stats() -> dict
```

### HookConfig

```python
class HookConfig:
    hooks: dict[str, list[HookRule]]
    enabled: bool = True
    log_executions: bool = True
    default_timeout: int = 30

    @classmethod
    def from_yaml(yaml_path) -> HookConfig
    def to_yaml(yaml_path) -> None
    def add_hook(event, hook, matcher=None, priority=0) -> None
```

## See Also

- [Continuous Learning](continuous-learning.md) - Pattern extraction
- [CLI Reference](reference/cli-reference.md#slash-command-system) - Slash command system
