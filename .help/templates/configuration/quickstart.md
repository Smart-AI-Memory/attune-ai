---
type: quickstart
name: configuration-quickstart
feature: configuration
depth: quickstart
generated_at: 2026-06-24T01:14:11.680426+00:00
source_hash: 7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1
status: generated
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
