---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: quickstart
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Quickstart

Load the unified config and validate it:

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

cfg = load_unified_config()        # searches CONFIG_SEARCH_PATHS
errors = validate_config(cfg)
print(type(cfg).__name__, "with", len(errors), "validation error(s)")
print(cfg.routing.to_dict())
```
