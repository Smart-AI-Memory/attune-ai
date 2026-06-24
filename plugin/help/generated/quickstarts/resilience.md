---
name: resilience
source: content/features/resilience.md
tags:
- resilience
- fault-tolerance
- retry
- circuit-breaker
- reliability
type: quickstart
---

# Fault-tolerance primitives — retries, circuit breakers, timeouts, fallbacks, and health checks

## Quickstart

Add retry to a flaky call with one decorator:

```python
from attune.resilience import retry


@retry(max_attempts=3, initial_delay=0.1)
def load_value() -> int:
    return 42


print(load_value())
```
