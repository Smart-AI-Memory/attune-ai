---
description: Context Management: Preserve collaboration state across context window resets and sessions.
---

# Context Management

Preserve collaboration state across context window resets and sessions.

## Overview

The context management system handles:

- **State Extraction**: Convert rich state to compact form
- **Persistence**: Save state to disk
- **Restoration**: Reload state in new sessions
- **SBAR Handoffs**: Structured work continuity

## Quick Start

```python
from attune.context import ContextManager

# Initialize
manager = ContextManager(storage_dir=".attune/compact_states")

# Set session info
manager.session_id = "session_abc123"
manager.current_phase = "implementation"
manager.complete_phase("planning")

# Create handoff for work continuity
manager.set_handoff(
    situation="Implementing user authentication",
    background="User requested OAuth2 support",
    assessment="50% complete, login flow working",
    recommendation="Continue with token refresh logic",
)

# Save state
path = manager.save_for_compaction(collaboration_state)
print(f"State saved to: {path}")
```

## Compact State

The `CompactState` preserves essential information:

```python
@dataclass
class CompactState:
    user_id: str
    trust_level: float           # 0.0 - 1.0
    empathy_level: int           # 1 - 5
    detected_patterns: list      # Top patterns
    session_id: str
    current_phase: str
    completed_phases: list[str]
    pending_handoff: WorkHandoff | None
    interaction_count: int
    successful_actions: int
    failed_actions: int
    preferences: dict
    saved_at: datetime
```

## SBAR Handoffs

Use SBAR format for clear work continuity:

| Component | Purpose | Example |
|-----------|---------|---------|
| **S**ituation | What's happening now | "Implementing OAuth2 login" |
| **B**ackground | Relevant context | "User needs Google/GitHub auth" |
| **A**ssessment | Current understanding | "Login flow complete, refresh pending" |
| **R**ecommendation | Suggested next action | "Implement token refresh" |

```python
handoff = manager.set_handoff(
    situation="Current task description",
    background="Why we're doing this",
    assessment="What's the current state",
    recommendation="What to do next",
    priority="high",  # low, normal, high, critical
)
```

## State Persistence

### Save State

```python
# From collaboration state
path = manager.save_for_compaction(collaboration_state)

# Or create manually
from attune.context import CompactState, CompactionStateManager

state = CompactState(
    user_id="user123",
    trust_level=0.85,
    empathy_level=4,
    # ... other fields
)

state_manager = CompactionStateManager()
path = state_manager.save_state(state)
```

### Storage Location

```
.attune/compact_states/
  {user_id}/
    state_{session_id}_{timestamp}.json
```

### Restore State

```python
# Latest state for user
state = manager.restore_state(user_id="user123")

# Specific session
state = manager.restore_by_session(session_id="session_abc")

# Generate restoration prompt
prompt = manager.generate_restoration_prompt(user_id="user123")
```

## Compaction Suggestions

The manager can suggest when to compact:

```python
should_compact = manager.should_suggest_compaction(
    token_usage_percent=65,  # Current usage
    message_count=50,        # Optional
)

if should_compact:
    message = manager.get_compaction_message(token_usage_percent=65)
    print(message)
    # "Context usage at 65%. Consider running `/compact`..."
```

## State Restoration Prompt

Generate a prompt for session continuity:

```python
prompt = manager.generate_restoration_prompt("user123")
```

Output format:
```
## Session Restoration

Previous session: session_abc
Trust level: 0.85
Empathy level: 4

### Completed Phases
- planning
- design

### Current Phase
implementation

### Pending Handoff
**Situation**: Implementing OAuth2
**Background**: User needs social login
**Assessment**: 50% complete
**Recommendation**: Continue with token refresh
```

## Integration with Hooks

### Pre-Compact Hook

```python
from attune.hooks import HookRegistry, HookEvent

registry = HookRegistry()

def pre_compact_handler(context):
    manager = context.get("context_manager")
    state = context.get("collaboration_state")

    # Save state before compaction
    manager.save_for_compaction(state)
    return {"success": True}

registry.register(
    event=HookEvent.PRE_COMPACT,
    handler=pre_compact_handler,
)
```

### Session Start Hook

```python
def session_start_handler(context):
    manager = ContextManager()
    user_id = context.get("user_id")

    # Try to restore previous state
    state = manager.restore_state(user_id)

    if state:
        return {
            "success": True,
            "restored": True,
            "session_id": state.session_id,
        }
    return {"success": True, "restored": False}
```

## Integration with Commands

The `/compact` command uses context management:

```python
from attune.commands import CommandContext

ctx = CommandContext(
    user_id="user123",
    context_manager=manager,
)

# Save state
ctx.save_context_state()

# Restore state
ctx.restore_context_state()
```

## Apply State to Collaboration

```python
# Restore state
compact_state = manager.restore_state(user_id)

# Apply to active collaboration
manager.apply_state_to_collaboration(
    compact_state=compact_state,
    collaboration_state=active_state,
)
```

## State Summary

```python
summary = manager.get_state_summary("user123")
# {
#     "user_id": "user123",
#     "states_count": 5,
#     "latest_saved": "2025-01-23T10:00:00",
#     "latest_trust_level": 0.85,
#     "latest_empathy_level": 4,
#     "patterns_count": 12,
#     "has_pending_handoff": True,
# }
```

## Clear States

```python
# Clear all states for a user
count = manager.clear_states("user123")
print(f"Cleared {count} states")
```

## API Reference

### ContextManager

```python
class ContextManager:
    def __init__(storage_dir=".attune/compact_states", token_threshold=50)

    # Properties
    session_id: str
    current_phase: str

    # Phase management
    def complete_phase(phase: str) -> None

    # Handoff
    def set_handoff(situation, background, assessment, recommendation, priority="normal") -> WorkHandoff
    def clear_handoff() -> None

    # State operations
    def extract_compact_state(collaboration_state) -> CompactState
    def save_for_compaction(collaboration_state) -> Path
    def restore_state(user_id) -> CompactState | None
    def restore_by_session(session_id) -> CompactState | None
    def apply_state_to_collaboration(compact_state, collaboration_state) -> None

    # Utilities
    def generate_restoration_prompt(user_id) -> str | None
    def should_suggest_compaction(token_usage_percent, message_count=None) -> bool
    def get_compaction_message(token_usage_percent) -> str
    def get_state_summary(user_id) -> dict | None
    def clear_states(user_id) -> int
```

### CompactionStateManager

```python
class CompactionStateManager:
    def __init__(storage_dir=".attune/compact_states")

    def save_state(state: CompactState) -> Path
    def load_latest_state(user_id: str) -> CompactState | None
    def load_state_by_session(session_id: str) -> CompactState | None
    def get_all_states(user_id: str) -> list[CompactState]
    def clear_user_states(user_id: str) -> int
```

## See Also

- [Hooks](hooks.md) - Event-driven extensibility
- [Continuous Learning](continuous-learning.md) - Pattern extraction
- [CLI Reference](reference/cli-reference.md#slash-command-system) - Slash command system
