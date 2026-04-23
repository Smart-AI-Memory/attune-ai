# Context Management and Compaction

Attune AI tracks session state and preserves it across context window resets
(compaction events). This guide explains how the context system works and how
to use it in long-running sessions.

---

## Why Context Management Matters

Claude Code has a finite context window. When a long session approaches the
limit, Claude Code fires a `PreCompact` hook before compressing the
conversation. Without intervention, all accumulated collaboration state —
detected patterns, pending work, trust level, session phase — is lost.

Attune's context layer captures that state before compaction and restores it
afterward so the session continues without a cold start.

---

## How It Works

```
Session running...
        │
        ▼ (context nearing limit)
┌───────────────────────────────────┐
│  PreCompact hook fires             │
│  ContextManager.save_before()      │
│  → CompactState saved to disk      │
└───────────────────────────────────┘
        │
        ▼ (Claude Code compresses context)
┌───────────────────────────────────┐
│  PostCompact hook fires            │
│  ContextManager.restore_after()    │
│  → State reloaded from disk        │
│  → Restoration prompt injected     │
└───────────────────────────────────┘
        │
        ▼
Session continues with full context
```

The state is persisted to `.attune/compact_states/` as JSON. Each state
snapshot captures:

- Current session ID and work phase
- Completed and pending phases
- Detected collaboration patterns
- SBAR handoff for pending work
- Trust metrics and empathy level

---

## Quick Start

The context system is automatic when hooks are configured. No code changes
are required for basic use.

### Verify It's Active

```bash
# Check hook configuration
attune validate

# See existing compact states
ls .attune/compact_states/
```

### Manual State Save

```python
from attune.context.manager import ContextManager

ctx = ContextManager(
    storage_dir=".attune/compact_states",
    token_threshold=80,  # Save state when context is 80% full
    auto_save=True,
)

# Save current state before a known reset
state_id = ctx.save_state(
    session_id="my-session-001",
    phase="implementing-auth",
    collaboration_state=llm.collaboration_state,
)
print(f"State saved: {state_id}")
```

### Restore After Compaction

```python
# On session restart, restore the last state
restored = ctx.restore_latest()

if restored:
    print(f"Restored session: {restored.session_id}")
    print(f"Last phase: {restored.current_phase}")
    print(restored.restoration_prompt)  # Inject into first message
```

---

## SBAR Handoff

Use an SBAR handoff when you are in the middle of a multi-step task
and want the restored session to continue exactly where you left off —
not just know the phase, but know what the next concrete action is.
The Situation-Background-Assessment-Recommendation format gives the
restored session enough context to act without re-reading the conversation.

```python
from attune.context.compaction import SBARHandoff

handoff = SBARHandoff(
    situation="Implementing JWT refresh token rotation",
    background="Auth module uses RS256 keys; current tokens expire in 1h",
    assessment="Rotation logic is written; edge case for concurrent requests unresolved",
    recommendation="Resolve concurrent refresh race condition, then run auth test suite",
    priority="high",
)

ctx.set_pending_handoff(handoff)

# The handoff is included in the next save and injected on restore
```

---

## CompactState

The `CompactState` dataclass is the unit of persistence:

```python
@dataclass
class CompactState:
    session_id: str
    created_at: datetime
    current_phase: str
    completed_phases: list[str]
    patterns: list[PatternSummary]   # Detected collaboration patterns
    pending_handoff: SBARHandoff | None
    trust_level: float               # 0.0–1.0
    empathy_level: int               # 1–5
    metadata: dict[str, Any]
```

### Listing Saved States

```python
states = ctx.list_states()
for state in states:
    print(f"{state.session_id}  phase={state.current_phase}  "
          f"saved={state.created_at.strftime('%Y-%m-%d %H:%M')}")
```

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `storage_dir` | `.attune/compact_states` | Where state files are written |
| `token_threshold` | 80 | % token usage that triggers a save suggestion |
| `auto_save` | `True` | Save automatically on `PreCompact` hook |

### Override Storage Location

```python
ctx = ContextManager(
    storage_dir="/tmp/my-session-states",
    auto_save=False,  # Manual saves only
)
```

---

## Hook Integration

The `PreCompact` hook script at
`src/attune/hooks/scripts/pre_compact.py` calls the context manager
automatically. When using a standard Attune setup, you don't need to wire
this manually.

To verify the hook is registered:

```bash
cat .claude/settings.json | python3 -m json.tool | grep -A 5 "PreCompact"
```

---

## See Also

- [Hooks](../reference/hooks.md) — How hook events fire during compaction
- [Patterns](../reference/pattern-library.md) — Collaboration pattern detection
- [Learning and Patterns](learning-and-patterns.md) — How patterns are extracted
  and persisted across sessions
