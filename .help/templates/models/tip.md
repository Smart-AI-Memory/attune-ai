---
type: tip
name: models-tip
feature: models
depth: tip
generated_at: 2026-06-04T23:45:26.769564+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Tip: working effectively with models

Use `get_auth_strategy()` to read the current authentication configuration instead of constructing an `AuthStrategy` directly — it returns the global instance and respects saved state from `AuthStrategy.load()`.

**Why it matters:** `AuthStrategy` stores thresholds (`small_module_threshold`, `medium_module_threshold`) and multipliers (`loc_to_tokens_multiplier`) that affect cost estimates and mode recommendations. Bypassing the global instance means those values may not reflect what the user configured interactively via `configure_auth_interactive()`.

**Tradeoff:** `get_auth_strategy()` reads from disk on first call. If you call it in a tight loop — for example, when routing many workflow stages — cache the result yourself rather than calling it repeatedly.
