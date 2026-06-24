---
type: quickstart
name: telemetry-quickstart
feature: telemetry
depth: quickstart
generated_at: 2026-06-24T00:53:03.849694+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Quickstart

Read your local usage from Python — the singleton reads the same store
the workflows write to:

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker.get_instance()      # process-wide singleton
stats = tracker.get_stats(days=30)
print(stats["total_calls"], "calls", stats["total_cost"], "USD")
```

Or from a conversation, call the `telemetry_stats` MCP tool, which reads
the same on-disk store (`~/.attune/telemetry/usage.jsonl`).
