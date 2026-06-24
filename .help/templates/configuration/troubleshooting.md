---
type: troubleshooting
name: configuration-troubleshooting
feature: configuration
depth: troubleshooting
generated_at: 2026-06-24T01:14:11.680426+00:00
source_hash: 7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1
status: generated
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `AttributeError` mixing the two configs | Treating a `UnifiedConfig` like an `AttuneConfig` (or vice versa) | They are different types — use one tree's API consistently | high |
| Env override ignored | Variable not `ATTUNE_`/`EMPATHY_`-prefixed, or set after load | Prefix correctly; reload after setting | medium |
| `validate_config` reports errors | A section value is out of range/invalid | Read each `ValidationError`; fix the named field | medium |
| `get_value`/`set_value` `KeyError` | Key path not in `get_all_keys()` | List `get_all_keys()` first | low |
| XML config changes not seen elsewhere | Replaced a local instance, not the global | Use `set_config()` to swap the global instance | medium |

### Risk areas

- **Two return types.** `load_config` → `AttuneConfig`;
  `load_unified_config` → `UnifiedConfig`. Don't cross their APIs.
- **Env precedence.** `ATTUNE_` wins over `EMPATHY_` wins over file.
- **Global XML config.** `get_config`/`set_config` operate on a shared
  instance; a local `EmpathyXMLConfig(...)` is not the global one.

### Diagnosis order

1. Which tree are you on? `type(cfg).__name__`.
2. For the unified tree, `validate_config(cfg)` then read each error.
3. For env issues, confirm the `ATTUNE_`/`EMPATHY_` prefix and load
   order.
4. For key-path issues, `cfg.get_all_keys()`.
