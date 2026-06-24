---
type: tip
name: help-system-tip
feature: help-system
depth: tip
generated_at: 2026-06-24T11:38:37.880839+00:00
source_hash: ca01c2128b2f7c655e8b49be4eed5c98e84af405f64d43f1ed48adce237ea1ab
status: generated
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
