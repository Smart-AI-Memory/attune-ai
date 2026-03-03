---
description: TierFallbackHelper Quick Start: ## Overview `TierFallbackHelper` provides simple convenience methods for tier-based fallback logic in Sprint 1 tests.
---

# TierFallbackHelper Quick Start

## Overview

`TierFallbackHelper` provides simple convenience methods for tier-based fallback logic in Sprint 1 tests. It complements the existing sophisticated `FallbackPolicy` by offering a lightweight alternative for basic use cases.

## Import

```python
from attune.models import TierFallbackHelper
```

## Core Methods

### 1. get_next_tier(current_tier)

Returns the next tier in the fallback progression chain.

**Progression:** cheap → capable → premium → None

```python
# Examples
TierFallbackHelper.get_next_tier("cheap")     # Returns: "capable"
TierFallbackHelper.get_next_tier("capable")   # Returns: "premium"
TierFallbackHelper.get_next_tier("premium")   # Returns: None (highest tier)
TierFallbackHelper.get_next_tier("unknown")   # Returns: None
```

### 2. should_fallback(error, tier)

Determines if fallback should be attempted based on error type and current tier.

**Fallback Triggers:**
- ✅ TimeoutError
- ✅ ConnectionError
- ✅ OSError
- ❌ ValueError, TypeError, etc. (logic errors)

**Special Rule:** Premium tier never falls back (it's the highest tier).

```python
# Network errors trigger fallback
TierFallbackHelper.should_fallback(TimeoutError(), "cheap")
# Returns: True

# Logic errors don't trigger fallback
TierFallbackHelper.should_fallback(ValueError(), "cheap")
# Returns: False

# Premium tier never falls back
TierFallbackHelper.should_fallback(TimeoutError(), "premium")
# Returns: False
```

## Usage Example

### Simple Fallback Loop

```python
from attune.models import TierFallbackHelper

def call_with_fallback(prompt: str) -> str:
    """Call LLM with automatic tier fallback on network errors."""
    tier = "cheap"
    last_error = None

    while tier:
        try:
            # Attempt LLM call with current tier
            response = llm_client.call(prompt, tier=tier)
            return response

        except Exception as e:
            last_error = e

            # Check if should fallback
            if not TierFallbackHelper.should_fallback(e, tier):
                # Non-network error or highest tier reached
                raise

            # Get next tier
            next_tier = TierFallbackHelper.get_next_tier(tier)
            if not next_tier:
                # No more tiers available
                raise RuntimeError(
                    f"All tiers exhausted. Last error: {last_error}"
                ) from last_error

            # Try next tier
            tier = next_tier
            print(f"Falling back to tier: {tier}")

    raise RuntimeError("Unexpected: No tier to try") from last_error
```

### Sprint 1 Test Example

```python
import pytest
from attune.models import TierFallbackHelper

def test_tier_fallback_progression():
    """Test that tier fallback follows correct progression."""
    # Start with cheap tier
    tier = "cheap"
    progression = [tier]

    # Follow fallback chain
    while True:
        next_tier = TierFallbackHelper.get_next_tier(tier)
        if not next_tier:
            break
        progression.append(next_tier)
        tier = next_tier

    # Verify progression
    assert progression == ["cheap", "capable", "premium"]

def test_network_error_triggers_fallback():
    """Test network errors trigger fallback."""
    network_errors = [
        TimeoutError("Request timeout"),
        ConnectionError("Connection refused"),
        OSError("Network unreachable"),
    ]

    for error in network_errors:
        assert TierFallbackHelper.should_fallback(error, "cheap")

def test_logic_error_does_not_trigger_fallback():
    """Test logic errors don't trigger fallback."""
    logic_errors = [
        ValueError("Invalid parameter"),
        TypeError("Wrong type"),
        KeyError("Missing key"),
    ]

    for error in logic_errors:
        assert not TierFallbackHelper.should_fallback(error, "cheap")
```

## When to Use

### Use TierFallbackHelper When:
- ✅ Writing simple Sprint 1 tests
- ✅ Need basic tier progression logic
- ✅ Want lightweight fallback without complex configuration
- ✅ Testing fallback behavior in isolation

### Use FallbackPolicy When:
- ✅ Building production workflows
- ✅ Need provider-level fallback (Anthropic → OpenAI)
- ✅ Want retry logic with exponential backoff
- ✅ Need circuit breaker functionality
- ✅ Require custom fallback chains

## Comparison: TierFallbackHelper vs FallbackPolicy

| Feature | TierFallbackHelper | FallbackPolicy |
|---------|-------------------|----------------|
| Complexity | Simple (2 methods) | Advanced (multi-strategy) |
| Setup | None required | Configuration needed |
| Tier fallback | ✅ Yes | ✅ Yes |
| Provider fallback | ❌ No | ✅ Yes |
| Retry logic | ❌ No | ✅ Yes |
| Circuit breaker | ❌ No | ✅ Yes (via ResilientExecutor) |
| Custom chains | ❌ No | ✅ Yes |
| Best for | Testing, simple use cases | Production workflows |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ attune.models                                   │
│                                                     │
│  ┌────────────────────┐   ┌──────────────────────┐ │
│  │ TierFallbackHelper │   │ FallbackPolicy       │ │
│  │                    │   │                      │ │
│  │ - Simple helpers   │   │ - Advanced policies  │ │
│  │ - Tier progression │   │ - Provider fallback  │ │
│  │ - Error filtering  │   │ - Retry strategies   │ │
│  └────────────────────┘   │ - Circuit breakers   │ │
│                           └──────────────────────┘ │
│                                                     │
│  Both can be used independently or together         │
└─────────────────────────────────────────────────────┘
```

## Tier Definitions

| Tier | Models | Use Case | Cost |
|------|--------|----------|------|
| cheap | Haiku 4.0, GPT-4 Mini, Gemini Flash | Simple tasks, high volume | Lowest |
| capable | Sonnet 4.5, GPT-4o, Gemini Pro | Most tasks, good balance | Medium |
| premium | Opus 4.5, GPT-4 Turbo, Gemini Ultra | Complex reasoning, critical tasks | Highest |

## Error Classification

### Network Errors (Trigger Fallback)
- `TimeoutError` - Request timeout
- `ConnectionError` - Connection failed
- `OSError` - Network unavailable

### Logic Errors (No Fallback)
- `ValueError` - Invalid parameter
- `TypeError` - Wrong type
- `KeyError` - Missing key
- `AttributeError` - Missing attribute
- All other exceptions not related to network/infrastructure

## Testing

Run the comprehensive test suite:

```bash
# Run TierFallbackHelper tests
python -m pytest tests/unit/models/test_tier_fallback_helper.py -v

# Run with coverage
python -m pytest tests/unit/models/test_tier_fallback_helper.py --cov=attune.models.fallback --cov-report=term-missing
```

Expected output:
```
17 passed in 0.86s
```

## FAQ

### Q: Can I use both TierFallbackHelper and FallbackPolicy?
**A:** Yes! They're independent and can coexist. Use TierFallbackHelper for simple tests and FallbackPolicy for production workflows.

### Q: Why does premium tier never fall back?
**A:** Premium is the highest quality tier. There's no higher tier to fall back to, so the error should be handled or re-raised.

### Q: Can I customize the tier progression?
**A:** Not with TierFallbackHelper (it's intentionally simple). Use FallbackPolicy with `FallbackStrategy.CUSTOM` for custom chains.

### Q: What if I want to fall back to a cheaper tier instead of a more expensive one?
**A:** TierFallbackHelper always progresses UP in quality. For cost-based fallback, use `FallbackPolicy` with `FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER`.

### Q: How do I add custom error types?
**A:** Subclass the network error types:
```python
class MyCustomTimeout(TimeoutError):
    pass

# Automatically triggers fallback
TierFallbackHelper.should_fallback(MyCustomTimeout(), "cheap")  # True
```

## See Also

- [Full Documentation](../src/attune/models/fallback.py) - Complete implementation
- [Test Suite](../tests/unit/models/test_tier_fallback_helper.py) - 17 comprehensive tests
- [FallbackPolicy Guide](./FallbackPolicy.md) - Advanced fallback strategies
- [Model Registry](./ModelRegistry.md) - Available models and tiers

## Version History

- **v1.0** (2026-01-16): Initial implementation for Sprint 1
  - Simple tier progression
  - Network error filtering
  - 17 tests, all passing
  - Fully backward compatible
