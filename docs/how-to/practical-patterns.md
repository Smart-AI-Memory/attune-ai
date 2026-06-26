---
description: Practical patterns for sharing memory across agents using
  the surviving Attune primitives.
---

# Practical Patterns for Multi-Agent Systems

*Ready-to-use building blocks for agents that share memory.*

---

## Overview

This chapter covers the memory primitives Attune ships today for
coordinating work across agents:

- `get_redis_memory()` — shared short-term memory backend
- `AccessTier` — permission tiers controlling what an agent may
  read, write, or validate
- `StagedPattern` — a discovered pattern awaiting validation before
  it enters the shared library
- `Pattern` / `PatternLibrary` — the validated pattern store

These primitives let independent agents accumulate and reuse
knowledge through a common memory layer.

---

## Pattern: The Knowledge Accumulator

**Problem**: Agents discover patterns during work. You want to
accumulate that knowledge in a shared store without duplicates.

**Solution**: Stage each discovery as a `StagedPattern`, keyed by a
fingerprint, so repeated discoveries deduplicate instead of piling
up.

```python
from attune import (
    get_redis_memory,
    AccessTier,
    StagedPattern,
    Pattern,
    PatternLibrary,
)
import hashlib


def fingerprint(pattern_type: str, name: str, description: str) -> str:
    """Generate a stable fingerprint for deduplication."""
    content = f"{pattern_type}:{name}:{description}".lower()
    return hashlib.md5(content.encode()).hexdigest()[:12]


def stage_discovery(
    pattern_type: str,
    name: str,
    description: str,
    confidence: float,
) -> StagedPattern:
    """Build a staged pattern from a discovery."""
    fp = fingerprint(pattern_type, name, description)
    return StagedPattern(
        pattern_id=f"pat_{fp}",
        agent_id="learning_agent",
        pattern_type=pattern_type,
        name=name,
        description=description,
        confidence=confidence,
        code=None,
        context={},
    )


# Usage
memory = get_redis_memory()
tier = AccessTier.CONTRIBUTOR

staged = stage_discovery(
    pattern_type="security",
    name="Input Sanitization",
    description="Sanitize user input before database queries",
    confidence=0.85,
)
print(f"Staged pattern: {staged.pattern_id} (tier: {tier.name})")
```

**Benefit**: Fingerprint keys make repeated discoveries idempotent,
so the shared store stays free of near-duplicate noise.

---

## Next Steps

- **[API Reference](../reference/multi-agent.md)**: Full class
  documentation
- **[Examples](../tutorials/examples/multi-agent-team-coordination.md)**:
  Complete working examples
