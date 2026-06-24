---
name: help-system
source: content/features/help-system.md
tags:
- help
- templates
- docs
type: tip
---

# The progressive-depth help engine that discovers features, generates depth-layered templates, and serves contextual help

## Notes & tips

- **Import from the owning submodule** (no top-level `__all__`), or use
  the `help.engine` facade for the contextual/feedback helpers.
- **Counts are properties.** `stale_features`, `stale_count`,
  `regenerated_count`, `current_count` — no `()`.
- **`populate` is nullable.** Always check for `None`.
- **Maintenance is hash-based.** It only regenerates features whose
  source actually changed; `dry_run=True` reports without writing.
