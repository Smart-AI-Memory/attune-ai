---
type: tip
name: configuration-tip
feature: configuration
depth: tip
generated_at: 2026-06-24T01:14:11.680426+00:00
source_hash: 7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1
status: generated
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
