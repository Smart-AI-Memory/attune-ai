---
type: comparison
feature: security-audit
depth: comparison
generated_at: 2026-04-14T14:40:15.603378+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit vs Monitoring: choosing the right approach

## Context

Attune AI provides two complementary security approaches: the SecurityAuditWorkflow for comprehensive code analysis, and the AlertEngine for runtime monitoring. Both protect your LLM applications but serve different phases of the security lifecycle.

## Feature comparison

| Feature | SecurityAuditWorkflow | AlertEngine |
|---------|----------------------|-------------|
| **Timing** | Pre-deployment static analysis | Runtime monitoring |
| **Scope** | Full codebase scan | Telemetry metrics |
| **Detection method** | Four specialized subagents | Threshold-based alerts |
| **Output format** | Structured markdown report with severity scores | Real-time notifications |
| **Storage** | Report generation only | SQLite database for alert history |
| **Integration** | SDK workflow execution | CLI commands + webhook/email |

## SecurityAuditWorkflow capabilities

The SecurityAuditWorkflow orchestrates four specialized subagents:
- **vuln-scanner**: Detects eval/exec and injection risks
- **secret-detector**: Finds hardcoded credentials and API keys
- **auth-reviewer**: Analyzes authentication patterns
- **remediation-planner**: Suggests actionable fixes with effort estimates

Each audit produces a unified report with:
- Overall security score (0-100)
- Findings organized by severity (CRITICAL, HIGH, MEDIUM, LOW)
- File paths and line numbers for each issue
- Prioritized remediation steps

## AlertEngine capabilities

The AlertEngine monitors live telemetry and triggers notifications when metrics exceed thresholds:
- **Real-time detection**: Monitors LLM call patterns and workflow metrics
- **Multiple channels**: Supports webhook and email notifications
- **Cooldown periods**: Prevents alert flooding (default 1 hour)
- **Alert management**: Enable/disable, view history, adjust thresholds
- **Persistent storage**: SQLite backend for alert configuration and history

## Use SecurityAuditWorkflow when...

- You need comprehensive pre-deployment security analysis
- Your codebase contains potential vulnerabilities (secrets, injections, path traversal)
- You want structured findings with severity scoring and remediation guidance
- You're preparing for security reviews or compliance audits
- You need detailed file-level analysis with line numbers

## Use AlertEngine when...

- You want continuous monitoring of production LLM applications
- You need immediate notification of anomalous behavior
- Your focus is runtime telemetry patterns rather than static code
- You want persistent alert configuration and historical tracking
- You need integration with external monitoring systems via webhooks

## Recommended approach

Use both systems together for comprehensive security coverage:

1. **Development phase**: Run SecurityAuditWorkflow to catch vulnerabilities before deployment
2. **Production phase**: Configure AlertEngine to monitor runtime behavior and detect anomalies

The SecurityAuditWorkflow catches what you can see in code, while AlertEngine catches what you can only see in production telemetry.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
