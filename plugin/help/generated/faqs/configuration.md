---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: faq
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
