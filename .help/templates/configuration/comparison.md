---
type: comparison
name: configuration-comparison
feature: configuration
depth: comparison
generated_at: 2026-06-24T01:14:11.680426+00:00
source_hash: 7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1
status: generated
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
