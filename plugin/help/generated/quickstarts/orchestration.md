---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: quickstart
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

## Quickstart

Inspect the agent templates and grab a strategy:

```python
from attune.orchestration import get_all_templates, get_strategy

templates = get_all_templates()
print(len(templates), "templates; e.g.", templates[0].id)

strategy = get_strategy("sequential")
print(type(strategy).__name__)
```
