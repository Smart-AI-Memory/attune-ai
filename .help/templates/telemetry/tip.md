---
type: tip
name: telemetry-tip
feature: telemetry
depth: tip
generated_at: 2026-06-24T00:53:03.849694+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Notes & tips

- **Depend on the documented public surface.** The supported API is the
  classes exported from `attune.telemetry`; the per-module internals
  (file layout, buffering) are implementation details.
- **Use the singleton for reads.** `UsageTracker.get_instance()` reads
  the same store workflows write to; constructing a fresh tracker with a
  different `telemetry_dir` reads a different store.
- **`flush()` before reading freshly written calls.** Writes are
  buffered.
- **Coordination needs Redis.** Gate `EventStreamer` /
  `HeartbeatCoordinator` use behind `TelemetryFeatures`.
