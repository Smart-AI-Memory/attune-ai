---
type: architecture
name: security-audit
tags: [security, workflow, monitoring]
source: src/attune/workflows/security_audit.py
---

# Security Audit architecture

Scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, injection risks.

## Purpose

The security audit subsystem orchestrates four specialized LLM subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) to produce a unified, severity-grouped report with CWE identifiers and actionable remediation steps. It owns the scanning workflow, subagent coordination, and report synthesis. It does **not** own telemetry storage, alert delivery, or secret-scrubbing of LLM call records — those are handled by the monitoring and telemetry layers described below.

## Key classes

| Class | Responsibility | File |
|-------|----------------|------|
| `SecurityAuditWorkflow` | Coordinates the four subagents and synthesizes their output into a single structured report with Summary, Security, and Suggestions sections. | `src/attune/workflows/security_audit.py` |
| `AlertEngine` | Persists alert configurations in SQLite, evaluates telemetry metrics against thresholds, and dispatches `AlertEvent` records when a threshold is breached. | `src/attune/monitoring/engine.py` |
| `AlertConfig` | Dataclass that holds one alert's full configuration (metric, threshold, channel, cooldown, severity); serializes to/from dict for SQLite persistence. | `src/attune/monitoring/models.py` |
| `AlertEvent` | Immutable dataclass capturing a single threshold-breach event (current value, threshold, severity, timestamp, message). | `src/attune/monitoring/models.py` |
| `AlertMetric` | Enum of the telemetry metrics that `AlertEngine` can monitor. | `src/attune/monitoring/models.py` |
| `AlertChannel` | Enum of supported notification channels (webhook, email, etc.). | `src/attune/monitoring/models.py` |
| `AlertSeverity` | Enum of severity levels (`WARNING` and above) used in both `AlertConfig` and `AlertEvent`. | `src/attune/monitoring/models.py` |
| `TelemetryBackend` | Protocol defining the two methods (`log_call`, `log_workflow`) that any storage backend must implement. | `src/attune/monitoring/multi_backend.py` |
| `MultiBackend` | Fan-out composite that writes to all registered `TelemetryBackend` instances; tracks per-backend failures without aborting the others. | `src/attune/monitoring/multi_backend.py` |
| `OTELBackend` | `TelemetryBackend` implementation that batches records and exports them to an OpenTelemetry collector with configurable retry logic. | `src/attune/monitoring/otel_backend.py` |

## Data flow

The audit path and the monitoring path are parallel concerns that share the `TelemetryBackend` protocol.

**Audit path** (triggered by `attune workflow run security-audit`):

```
attune CLI
    │
    ▼
SecurityAuditWorkflow.execute(path=...)
    │  dispatches task prompt to each subagent in sequence
    ├──▶ vuln-scanner        (eval/exec, injection, SSRF)
    ├──▶ secret-detector     (hardcoded secrets, API keys)
    ├──▶ auth-reviewer       (auth/authz patterns)
    └──▶ remediation-planner (prioritized fix suggestions)
    │
    ▼
Orchestrator synthesizes findings
    │
    ▼
Unified report: Summary / Security (by severity) / Suggestions
```

**Monitoring path** (alert evaluation on telemetry data):

```
LLM call / workflow run
    │
    ▼
MultiBackend.log_call() / log_workflow()
    ├──▶ OTELBackend   (batched export to OTEL collector)
    └──▶ [other TelemetryBackend implementations]

alert watch loop
    │
    ▼
AlertEngine.get_metrics()         (reads telemetry from disk)
    │
    ▼
AlertEngine.check_and_trigger()   (compares each AlertConfig threshold)
    │
    ▼
AlertEvent recorded in SQLite
    │
    └──▶ notification dispatched via AlertChannel (webhook / email)
```

## Design decisions

**Four fixed subagents rather than a single general-purpose agent.** The subagent names (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) are declared as a module-level constant (`_SUBAGENT_NAMES`). Splitting responsibilities this way keeps each agent's context window focused and makes the prompt template predictable. A single-agent approach was rejected because combining vulnerability scanning, secret detection, auth review, and remediation planning in one prompt produces lower-quality output on large codebases.

**Orchestrator-synthesized report, not per-agent reports.** The system prompt instructs a senior-security-orchestrator persona to merge subagent output into one report (Summary → Security → Suggestions). This means callers always receive a single artifact; they never need to merge multiple responses. The trade-off is that the orchestrator's synthesis step adds latency.

**SQLite for alert persistence.** `AlertEngine` writes `AlertConfig` and `AlertEvent` records to a local SQLite file (default: `.attune/alerts.db`). This avoids an external service dependency for the common single-developer case. Teams that need distributed alert state must replace `AlertEngine` or its storage layer.

**`MultiBackend` failure isolation.** When one `TelemetryBackend` raises, `MultiBackend` records it in a failed-backends list and continues writing to the remaining backends. This prevents a flaky OTEL collector from silently dropping local telemetry. Call `reset_failures()` to re-enable a previously failed backend.

## Extension points

- **Add a new scan category:** Add the subagent name to `_SUBAGENT_NAMES` in `src/attune/workflows/security_audit.py` and update `_TASK_PROMPT_TEMPLATE` to describe its domain and expected output format.

- **Add a new telemetry storage backend:** Implement the `TelemetryBackend` protocol (`log_call`, `log_workflow`), then register an instance via `MultiBackend.add_backend()`. The `OTELBackend` is the canonical example to follow.

- **Add a new notification channel:** Extend the `AlertChannel` enum in `src/attune/monitoring/models.py`, then add the corresponding dispatch branch inside `AlertEngine.check_and_trigger()`.

- **Add a new monitorable metric:** Extend the `AlertMetric` enum and update `AlertEngine.get_metrics()` to compute and return the new metric's value.

- **Configure alerts programmatically:** Call `AlertEngine.add_alert()` directly instead of going through the CLI. `get_alert_engine()` returns a ready-to-use instance pointed at the default database path.

For usage, see `attune help-docs ref-skill-security-audit` or the quickstart at `quickstarts/run-security-audit.md`.

<!-- attune-generated: source_hash=b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668 feature=security-audit kind=architecture generated_at=2026-05-16 -->
