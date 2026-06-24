---
name: telemetry
source: content/features/telemetry.md
tags:
- telemetry
- metrics
type: tip
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
