---
type: quickstart
name: resilience-quickstart
feature: resilience
depth: quickstart
generated_at: 2026-06-24T01:31:58.105100+00:00
source_hash: 5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6
status: generated
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
