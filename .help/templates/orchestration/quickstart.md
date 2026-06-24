---
type: quickstart
name: orchestration-quickstart
feature: orchestration
depth: quickstart
generated_at: 2026-06-24T04:42:36.420317+00:00
source_hash: 8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103
status: generated
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
