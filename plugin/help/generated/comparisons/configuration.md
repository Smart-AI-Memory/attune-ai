---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: comparison
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Comparison

Four layers, distinct jobs:

| | Unified config | Agent config | XML/empathy config | Legacy dataclass |
|--|----------------|--------------|--------------------|------------------|
| Class | `UnifiedConfig` | `UnifiedAgentConfig` | `EmpathyXMLConfig` | `AttuneConfig` |
| Entry | `load_unified_config()` | construct / `for_book_production` | `get_config()` | `load_config()` |
| Scope | App-wide sections | LLM agent runtime | Empathy subsystem | Back-compat |
| Status | Modern (preferred) | Active | Active (subsystem) | Legacy |

`load_config()` and `load_unified_config()` return **different types**
(`AttuneConfig` vs `UnifiedConfig`) — they are not interchangeable.
