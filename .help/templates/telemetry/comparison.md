---
type: comparison
feature: telemetry
depth: comparison
generated_at: 2026-04-20T01:25:26.620997+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry vs other coordination options

Attune offers multiple ways to track agent activity and coordinate workflows. Telemetry provides the most comprehensive monitoring but comes with setup overhead that simpler alternatives avoid.

## Feature comparison

| Capability | Telemetry | Direct Redis | Manual logging | No tracking |
|---|---|---|---|---|
| **Agent coordination** | TTL-based signals, heartbeats | Raw key operations | None | None |
| **Human approval gates** | Built-in workflow control | Custom implementation required | Not supported | Not supported |
| **Real-time streaming** | Redis Streams with typed events | Manual pub/sub setup | Log file tailing | None |
| **Performance analytics** | Cost tracking, model tier analysis | Manual metric collection | Basic timing only | None |
| **Setup complexity** | Moderate (Redis + structured classes) | Low (Redis only) | Low (file writes) | None |
| **Memory overhead** | ~2MB per active coordinator | Minimal | Minimal | None |
| **Debugging visibility** | Full workflow traces | Key inspection only | Text search in logs | None |

## Use telemetry when you need

**Multi-agent coordination at scale.** Telemetry's `CoordinationSignals` and `HeartbeatCoordinator` handle complex workflows where agents must wait for each other, track progress, and recover from failures. The TTL-based cleanup prevents orphaned processes that manual coordination often leaves behind.

**Human-in-the-loop workflows.** `ApprovalGate` provides structured approval requests with timeouts and context. Unlike ad-hoc prompting, it maintains audit trails and handles concurrent approval requests without race conditions.

**Production monitoring with cost awareness.** The CLI analysis commands (`cmd_sonnet_opus_analysis`, `cmd_agent_performance`) give you model usage breakdowns and cost optimization insights that simple logging cannot provide.

## Use direct Redis when you need

**Simple coordination without structure.** If you're just setting flags or sharing small data between processes, Redis operations like `SET` with `EX` (expiration) give you the coordination benefits without telemetry's class overhead.

**Custom data models.** Telemetry's dataclasses (`CoordinationSignal`, `AgentHeartbeat`) work well for common patterns but may not fit specialized coordination needs.

## Use manual logging when you need

**Development debugging only.** File-based logs are sufficient for understanding single-agent behavior during development. The `logging` module is already configured and requires no additional dependencies.

**Append-only audit trails.** If you need permanent records that survive Redis restarts, file logging with rotation gives you durability that in-memory coordination cannot.

## Skip tracking entirely when

**Prototyping or single-use scripts.** The coordination overhead isn't worth it for exploratory work or one-off tasks that won't run in production.

**Performance is critical.** Even minimal telemetry adds latency to every coordination point. Pure computation without coordination needs avoids this entirely.

## Recommendation

**Start with telemetry if you have more than one agent or any human approval steps.** The structured approach scales better than growing from manual coordination. The CLI commands alone justify the setup cost for production systems.

**Use direct Redis for simple producer/consumer patterns** where you're just passing data between processes without complex coordination logic.

**Reserve manual logging for development debugging** and permanent audit requirements that survive system restarts.

The telemetry feature is designed for production multi-agent systems. If you're unsure whether you need it, you probably don't — but when coordination complexity grows, migrating from manual approaches becomes significantly more work than starting with the structured telemetry classes.
