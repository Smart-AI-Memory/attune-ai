---
type: quickstart
name: memory-quickstart
feature: memory
depth: quickstart
generated_at: 2026-06-23T21:52:16.487778+00:00
source_hash: 544951b28662066a703ef7be552af08e83ef52a5186e5ad71ad216119352938b
status: generated
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
