---
type: tip
name: ops-dashboard-tip
feature: ops-dashboard
depth: tip
generated_at: 2026-05-16T06:19:45.816009+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Tip: Start the ops dashboard with `build_config`, not by constructing `Config` directly

Pass your parameters through `build_config()` rather than instantiating `Config` yourself. `build_config()` resolves environment defaults — including `attune_home` and `specs_roots` — that are easy to misconfigure when you set fields by hand.

**Why:** `Config` is a dataclass, so Python lets you construct it directly, but `build_config()` is where environment variable resolution and default wiring actually happen. Skipping it produces a `Config` that looks valid but silently misses those defaults.

**Tradeoff:** `build_config()` is an opaque builder — you can't see all the resolution logic at a glance. When you need to understand exactly what a field resolves to (for example, why `attune_home` is pointing somewhere unexpected), read `src/attune/ops/config.py` alongside it rather than relying on the defaults alone.
