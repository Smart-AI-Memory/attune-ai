---
type: tip
feature: telemetry
depth: tip
generated_at: 2026-04-14T15:21:43.418754+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Tip: working effectively with telemetry

Use the CLI commands for analysis, but build coordination logic with the classes for real-time agent coordination. The telemetry module splits cleanly between reporting (CLI functions) and runtime coordination (signal classes).

## Why

The CLI functions like `cmd_sonnet_opus_analysis()` and `cmd_agent_performance()` are designed for post-hoc analysis and cost reporting, while classes like `CoordinationSignals` and `HeartbeatCoordinator` handle live agent-to-agent communication with TTL-based Redis coordination.

## The tradeoff

You'll write more code using the coordination classes directly instead of just running CLI commands, but you get real-time agent coordination with automatic cleanup via Redis TTL expiration — something the analysis commands can't provide.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
