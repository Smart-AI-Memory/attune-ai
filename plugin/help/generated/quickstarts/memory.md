---
name: memory
source: content/features/memory.md
tags:
- memory
- storage
type: quickstart
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

## Quickstart

Create a memory for a user, stash some working data, and persist a
durable pattern. Every call is synchronous:

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory(user_id="agent@company.com")

# Short-term working memory (expires)
memory.stash("current_task", {"id": 42, "phase": "review"}, ttl_seconds=3600)
task = memory.retrieve("current_task")

# Long-term pattern memory (durable, classified)
result = memory.persist_pattern(
    content="Use heapq.nlargest for top-N instead of sorted()[:N]",
    pattern_type="optimization",
)
if result:
    pattern = memory.recall_pattern(result["pattern_id"])

memory.close()
```

`UnifiedMemory()` with no `config` auto-detects the environment, so the
same code runs against an in-process store in development and Redis in
production.
