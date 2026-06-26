---
description: Trust Circuit Breaker Guide: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Trust Circuit Breaker Guide

A cross-domain transfer of the circuit breaker pattern from reliability engineering to human-AI trust management. This guide covers setup, configuration, and integration patterns.

## Overview

The Trust Circuit Breaker protects the AI-user relationship by dynamically adjusting AI autonomy based on trust levels. When trust is damaged (wrong answers, ignored preferences), the system reduces AI autonomy and requires more confirmations. As trust rebuilds through successful interactions, autonomy is gradually restored.

## Quick Start

```python
from attune.trust import TrustCircuitBreaker, TrustDamageType

# Create a trust breaker for a user
breaker = TrustCircuitBreaker(user_id="user_123")

# Check if an action needs confirmation
if breaker.should_require_confirmation("file_write"):
    # Ask user for confirmation before proceeding
    confirmed = await ask_user("Should I write this file?")
    if not confirmed:
        return

# Proceed with action...
write_file(path, content)

# Record the outcome
if user_accepted_result:
    breaker.record_success("File written successfully")
else:
    breaker.record_damage(TrustDamageType.UNEXPECTED_ACTION, "User rejected file write")
```

## Trust States

The system uses three trust states, mapped from circuit breaker terminology:

| Trust State | Circuit Breaker | Description | Confirmation Required |
|-------------|-----------------|-------------|----------------------|
| `FULL_AUTONOMY` | CLOSED | Normal operation, AI acts freely | None |
| `REDUCED_AUTONOMY` | OPEN | Trust damaged, all actions need confirmation | All actions |
| `SUPERVISED` | HALF_OPEN | Testing recovery, high-impact actions need confirmation | High-impact only |

### State Transitions

```
                    damage threshold reached
FULL_AUTONOMY ─────────────────────────────────→ REDUCED_AUTONOMY
      ↑                                                  │
      │                                      recovery period elapsed
      │                                                  ↓
      └────────────── supervised successes ────── SUPERVISED
```

## Configuration

### Basic Configuration

```python
from attune.trust import TrustCircuitBreaker, TrustConfig

config = TrustConfig(
    # How many damage "points" before reducing autonomy
    damage_threshold=3,

    # Time window for counting damage (older events decay)
    damage_window_hours=24.0,

    # How long to stay in reduced autonomy before testing recovery
    recovery_period_hours=24.0,

    # Successful interactions needed in supervised mode
    supervised_successes_required=5,
)

breaker = TrustCircuitBreaker(
    user_id="user_123",
    config=config,
    domain="code_review",  # Optional: domain-specific trust
)
```

### Damage Severity Weights

Different types of trust damage have different weights:

```python
from attune.trust import TrustConfig, TrustDamageType

config = TrustConfig(
    severity_weights={
        TrustDamageType.WRONG_ANSWER: 1.0,        # Standard weight
        TrustDamageType.IGNORED_PREFERENCE: 1.5,  # Preferences matter
        TrustDamageType.UNEXPECTED_ACTION: 1.2,   # Surprises are bad
        TrustDamageType.SLOW_RESPONSE: 0.3,       # Minor annoyance
        TrustDamageType.MISUNDERSTOOD_INTENT: 0.8,
        TrustDamageType.REPETITIVE_ERROR: 2.0,    # Very damaging
    }
)
```

### High-Impact Actions

Define which actions require confirmation in supervised mode:

```python
config = TrustConfig(
    high_impact_actions=[
        "file_write",
        "file_delete",
        "git_commit",
        "git_push",
        "external_api_call",
        "code_execution",
        "database_write",
    ]
)
```

## Recording Trust Events

### Recording Damage

```python
from attune.trust import TrustDamageType

# Basic damage recording
breaker.record_damage(TrustDamageType.WRONG_ANSWER)

# With context for debugging
breaker.record_damage(
    TrustDamageType.WRONG_ANSWER,
    context="Suggested Python 2 syntax for Python 3 project"
)

# With custom severity (0.0 to 1.0)
breaker.record_damage(
    TrustDamageType.SLOW_RESPONSE,
    severity=0.5  # Half the normal impact
)

# User explicitly indicated damage
breaker.record_damage(
    TrustDamageType.IGNORED_PREFERENCE,
    user_explicit=True  # User clicked "This was wrong"
)
```

### Damage Types

| Type | Description | Default Weight |
|------|-------------|----------------|
| `WRONG_ANSWER` | AI provided incorrect information | 1.0 |
| `IGNORED_PREFERENCE` | AI acted against stated preferences | 1.5 |
| `UNEXPECTED_ACTION` | AI did something user didn't expect | 1.2 |
| `SLOW_RESPONSE` | AI was too slow | 0.3 |
| `MISUNDERSTOOD_INTENT` | AI misinterpreted user's request | 0.8 |
| `REPETITIVE_ERROR` | AI made the same mistake again | 2.0 |

### Recording Success

```python
# Basic success
breaker.record_success()

# With context
breaker.record_success("Code review accepted without changes")

# User explicitly praised
breaker.record_success(
    context="User clicked thumbs up",
    user_explicit=True
)
```

## Checking Trust State

### Simple Confirmation Check

```python
if breaker.should_require_confirmation("file_write"):
    # This action needs user confirmation
    pass
```

### Detailed Autonomy Information

```python
info = breaker.get_autonomy_level()

# Returns:
{
    "state": "supervised",
    "can_act_freely": False,
    "damage_score": 2.5,
    "damage_threshold": 3,
    "time_in_state_hours": 12.5,
    "recovery_progress": {
        "status": "supervised_testing",
        "progress": 0.7,
        "successes": 3,
        "required": 5
    },
    "recent_damage_count": 2
}
```

### State Change Callbacks

```python
def on_trust_change(old_state, new_state):
    if new_state == TrustState.REDUCED_AUTONOMY:
        notify_user("I'll ask for confirmation more often until trust rebuilds.")
    elif new_state == TrustState.FULL_AUTONOMY:
        notify_user("Trust restored! I can act more independently now.")

breaker.on_state_change(on_trust_change)
```

## Domain-Specific Trust

Track trust separately for different domains:

```python
# User trusts AI for documentation but not for code changes
doc_trust = TrustCircuitBreaker(user_id="user_123", domain="documentation")
code_trust = TrustCircuitBreaker(user_id="user_123", domain="code_review")

# Damage in one domain doesn't affect the other
code_trust.record_damage(TrustDamageType.WRONG_ANSWER)

code_trust.state  # REDUCED_AUTONOMY
doc_trust.state   # FULL_AUTONOMY (unaffected)
```

## Persistence

### Saving State

```python
# Serialize to dict (for JSON storage)
data = breaker.to_dict()

# Save to database, file, Redis, etc.
await db.save_trust_state(user_id, data)
```

### Restoring State

```python
# Load from storage
data = await db.get_trust_state(user_id)

# Restore breaker
breaker = TrustCircuitBreaker.from_dict(data)
```

### Example: Redis Persistence

```python
import json
import redis

class TrustStore:
    def __init__(self):
        self.redis = redis.Redis()

    def save(self, breaker: TrustCircuitBreaker):
        key = f"trust:{breaker.user_id}:{breaker.domain}"
        self.redis.set(key, json.dumps(breaker.to_dict()))

    def load(self, user_id: str, domain: str = "general") -> TrustCircuitBreaker:
        key = f"trust:{user_id}:{domain}"
        data = self.redis.get(key)
        if data:
            return TrustCircuitBreaker.from_dict(json.loads(data))
        return TrustCircuitBreaker(user_id=user_id, domain=domain)
```

## Integration Patterns

### With Workflow Execution

```python
from attune.trust import TrustCircuitBreaker, TrustDamageType

class TrustAwareWorkflow:
    def __init__(self, user_id: str):
        self.trust = TrustCircuitBreaker(user_id=user_id)

    async def execute_action(self, action: str, execute_fn):
        # Check if confirmation needed
        if self.trust.should_require_confirmation(action):
            confirmed = await self.ask_confirmation(action)
            if not confirmed:
                return {"status": "cancelled", "reason": "user_declined"}

        try:
            result = await execute_fn()
            self.trust.record_success(f"Action {action} succeeded")
            return result
        except Exception as e:
            self.trust.record_damage(
                TrustDamageType.UNEXPECTED_ACTION,
                context=f"Action {action} failed: {e}"
            )
            raise
```

### With LLM Responses

```python
class TrustAwareLLM:
    def __init__(self, user_id: str):
        self.trust = TrustCircuitBreaker(user_id=user_id)

    async def respond(self, query: str) -> str:
        response = await self.llm.complete(query)

        # In reduced autonomy, add uncertainty markers
        if self.trust.state == TrustState.REDUCED_AUTONOMY:
            response = self.add_uncertainty_markers(response)

        return response

    def add_uncertainty_markers(self, response: str) -> str:
        return (
            "Based on my understanding (please verify):\n\n"
            f"{response}\n\n"
            "Let me know if this doesn't match what you're looking for."
        )

    async def process_feedback(self, was_helpful: bool):
        if was_helpful:
            self.trust.record_success()
        else:
            self.trust.record_damage(TrustDamageType.WRONG_ANSWER)
```

## UI Integration

### Displaying Trust Status

```python
def render_trust_badge(trust: TrustCircuitBreaker) -> str:
    info = trust.get_autonomy_level()

    if info["state"] == "full_autonomy":
        return "Full Trust"
    elif info["state"] == "supervised":
        progress = info["recovery_progress"]
        return f"Rebuilding Trust ({progress['successes']}/{progress['required']})"
    else:
        progress = info["recovery_progress"]
        hours = progress.get("time_remaining_hours", 0)
        return f"Reduced Autonomy ({hours:.1f}h remaining)"
```

### Confirmation Dialog

```python
async def show_confirmation_dialog(action: str, trust: TrustCircuitBreaker):
    info = trust.get_autonomy_level()

    message = f"Should I proceed with: {action}?"

    if info["state"] == "reduced_autonomy":
        message += "\n\n(Asking because recent interactions had issues)"
    elif info["state"] == "supervised":
        message += "\n\n(Confirming high-impact actions while rebuilding trust)"

    return await show_dialog(message, buttons=["Yes", "No"])
```

## Convenience Functions

### Quick Setup

```python
from attune.trust import create_trust_breaker

# Standard configuration
breaker = create_trust_breaker(user_id="user_123")

# Strict configuration (fewer mistakes allowed, longer recovery)
strict_breaker = create_trust_breaker(user_id="user_123", strict=True)

# Domain-specific
code_breaker = create_trust_breaker(user_id="user_123", domain="code_review")
```

## Best Practices

### 1. Record Both Success and Failure

```python
# Don't just track failures - successes matter for recovery
try:
    result = await action()
    trust.record_success()
except:
    trust.record_damage(TrustDamageType.UNEXPECTED_ACTION)
```

### 2. Use Domain Isolation for Different Contexts

```python
# Separate trust for different capabilities
code_trust = create_trust_breaker(user_id, domain="code")
doc_trust = create_trust_breaker(user_id, domain="documentation")
chat_trust = create_trust_breaker(user_id, domain="chat")
```

### 3. Persist State Across Sessions

```python
# Save on every state change
trust.on_state_change(lambda old, new: store.save(trust))

# Load at session start
trust = store.load(user_id) or create_trust_breaker(user_id)
```

### 4. Make Trust Visible to Users

```python
# Users should understand why confirmations are happening
if trust.state != TrustState.FULL_AUTONOMY:
    show_trust_indicator(trust.get_autonomy_level())
```

### 5. Allow Manual Reset (with Caution)

```python
# For admin/support use
if user_requests_trust_reset and user_is_admin:
    trust.reset()
    log.info(f"Trust manually reset for {user_id}")
```

## Metrics and Monitoring

Track these metrics for insights:

```python
# Trust state distribution
trust_states = Counter(
    breaker.state for breaker in all_breakers
)

# Average damage score
avg_damage = mean(b.damage_score for b in all_breakers)

# Recovery success rate
recovered = sum(1 for b in breakers_in_supervised if b.state == TrustState.FULL_AUTONOMY)
recovery_rate = recovered / len(breakers_in_supervised)

# Time to recovery
avg_recovery_time = mean(
    b.time_in_current_state for b in recently_recovered
)
```

## Troubleshooting

### Trust Degrades Too Quickly

- Reduce `damage_threshold`
- Lower severity weights for minor issues
- Increase `damage_window_hours`

### Recovery Takes Too Long

- Reduce `recovery_period_hours`
- Lower `supervised_successes_required`
- Ensure you're calling `record_success()` on positive interactions

### State Not Persisting

- Verify `to_dict()` and `from_dict()` are being called
- Check storage layer for errors
- Ensure state is saved on every change

## API Reference

See [src/attune/trust/circuit_breaker.py](../../src/attune/trust/circuit_breaker.py) for full API documentation.

---

*This feature implements Level 5 (Systems Thinking) by transferring the circuit breaker pattern from reliability engineering to trust management.*
