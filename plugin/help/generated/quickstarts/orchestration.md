---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: quickstart
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Quickstart

Inspect the agent templates and grab a strategy:

```python
from attune.orchestration import get_all_templates, get_strategy

templates = get_all_templates()
print(len(templates), "templates; e.g.", templates[0].id)

strategy = get_strategy("sequential")
print(type(strategy).__name__)
```
