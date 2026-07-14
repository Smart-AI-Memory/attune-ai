---
type: faq
name: configuration-faq
feature: configuration
depth: faq
generated_at: 2026-07-14T15:58:49.715365+00:00
source_hash: 7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1
status: generated
---

# Configuration FAQ

## Which config should I use?

The unified tree — `load_unified_config()` → `UnifiedConfig`
with typed sections. `AttuneConfig`/`load_config()` is the legacy
dataclass; `EmpathyXMLConfig` (`get_config()`) is the empathy
subsystem's config.

## Why are there `AttuneConfig` and `EmpathyConfig`?

They are the **same class** — `EmpathyConfig` is an alias of
`AttuneConfig` (the legacy dataclass).

## How do environment overrides work?

`ATTUNE_`-prefixed variables override file values; the legacy
`EMPATHY_` prefix is honored as a fallback (`get_attune_env`).

## Where does config load from?

`CONFIG_SEARCH_PATHS` — `./attune.config.json`,
`~/.attune/config.json`, `~/.config/attune/config.json`.
