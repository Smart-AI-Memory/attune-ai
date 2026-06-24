---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: tip
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Notes & tips

- **Prefer the unified tree for new code.** `UnifiedConfig` +
  `load_unified_config` + `validate_config` is the modern path.
- **`AttuneConfig` ≡ `EmpathyConfig`.** Same class, two names.
- **`load_config` and `load_unified_config` differ.** Different return
  types; pick one and stay consistent.
- **Use `set_config()` for the XML config.** It swaps the global
  instance other code reads.
