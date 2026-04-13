---
feature: telemetry
depth: reference
generated_at: 2026-04-13T17:02:02.388039+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CoordinationSignal` | Coordination signal between agents. | `src/attune/telemetry/agent_coordination.py` |
| `CoordinationSignals` | TTL-based inter-agent coordination signals. | `src/attune/telemetry/agent_coordination.py` |
| `AgentHeartbeat` | Agent heartbeat data structure. | `src/attune/telemetry/agent_tracking.py` |
| `HeartbeatCoordinator` | Coordinates agent heartbeats using Redis TTL keys. | `src/attune/telemetry/agent_tracking.py` |
| `ApprovalRequest` | Approval request with context for human decision. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalResponse` | Response to an approval request. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalGate` | Human approval gates for workflow control. | `src/attune/telemetry/approval_gates.py` |
| `StreamEvent` | Event published to Redis Stream. | `src/attune/telemetry/event_streaming.py` |
| `EventStreamer` | Real-time event streaming using Redis Streams. | `src/attune/telemetry/event_streaming.py` |
| `FeatureStatus` | Status of an optional feature. | `src/attune/telemetry/features.py` |
| `FeatureInfo` | Information about a telemetry feature. | `src/attune/telemetry/features.py` |
| `TelemetryFeatures` | Check availability of telemetry features. | `src/attune/telemetry/features.py` |
| `FeedbackLoop` | Agent-to-LLM feedback loop for quality-based learning. | `src/attune/telemetry/feedback_loop.py` |
| `ModelTier` | Model tier enum matching workflows.base.ModelTier. | `src/attune/telemetry/feedback_models.py` |
| `FeedbackEntry` | Quality feedback for an LLM response. | `src/attune/telemetry/feedback_models.py` |
| `QualityStats` | Quality statistics for a workflow stage. | `src/attune/telemetry/feedback_models.py` |
| `TierRecommendation` | Tier recommendation based on quality feedback. | `src/attune/telemetry/feedback_models.py` |
| `UsageTracker` | Privacy-first local telemetry tracker. | `src/attune/telemetry/usage_tracker.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `main()` | Telemetry CLI entry point. | `src/attune/telemetry/__main__.py` |
| `cmd_sonnet_opus_analysis()` | Show Sonnet 4.5 to Opus 4.5 fallback analysis and cost savings. | `src/attune/telemetry/cli_analysis.py` |
| `cmd_file_test_status()` | Show per-file test status. | `src/attune/telemetry/cli_analysis.py` |
| `cmd_tier1_status()` | Show comprehensive Tier 1 automation status. | `src/attune/telemetry/cli_automation.py` |
| `cmd_task_routing_report()` | Show detailed task routing report. | `src/attune/telemetry/cli_automation.py` |
| `cmd_test_status()` | Show test execution status. | `src/attune/telemetry/cli_automation.py` |
| `cmd_agent_performance()` | Show agent performance metrics. | `src/attune/telemetry/cli_automation.py` |
| `cmd_telemetry_show()` | Show recent telemetry entries. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_savings()` | Calculate and display cost savings. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_cache_stats()` | Show prompt caching performance statistics. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_compare()` | Compare telemetry across two time periods. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_reset()` | Reset/clear all telemetry data. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_export()` | Export telemetry data to JSON or CSV. | `src/attune/telemetry/cli_core.py` |


## Source files

- `src/attune/telemetry/**`

## Tags

`telemetry`, `metrics`
