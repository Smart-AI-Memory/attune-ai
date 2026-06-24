---
name: telemetry
source: content/features/telemetry.md
tags:
- telemetry
- metrics
type: quickstart
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
