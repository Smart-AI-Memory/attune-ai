---
type: note
name: security-audit-note
feature: security-audit
depth: note
generated_at: 2026-05-16T06:19:45.819669+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Note: security audit

## Context

The security audit feature scans a codebase for vulnerabilities including `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks. It produces severity-grouped findings with CWE identifiers. See `concepts/tool-security-audit.md` for a full description of what it finds and how deep it goes.

## How the workflow is implemented

`SecurityAuditWorkflow` (defined in `src/attune/workflows/security_audit.py`) coordinates four specialized subagents in sequence:

| Subagent | Role |
|---|---|
| `vuln-scanner` | Detects injection risks, path traversal, and unsafe builtins |
| `secret-detector` | Finds hardcoded API keys, tokens, and passwords |
| `auth-reviewer` | Reviews authentication and authorization patterns |
| `remediation-planner` | Produces prioritized fix suggestions with effort estimates |

After the subagents finish, the orchestrator synthesizes their output into a single report with three sections: **Summary** (security score and executive overview), **Security** (findings by severity: CRITICAL, HIGH, MEDIUM, LOW), and **Suggestions** (remediation steps ordered by priority).

The system prompt instructs the orchestrator to cite file paths and line numbers wherever possible (`_SYSTEM_PROMPT`, `src/attune/workflows/security_audit.py`).

## Relationship to the alert and telemetry systems

The security audit workflow sits alongside — but is separate from — the LLM telemetry monitoring system in `src/attune/monitoring/`. That subsystem (`AlertEngine`, `AlertMetric`, `AlertChannel`, `AlertSeverity`, `AlertConfig`) monitors runtime LLM call metrics and triggers threshold-based notifications. It is not invoked during a security audit scan; the two systems share the same package but serve different purposes.

## Source files

- `src/attune/workflows/security_audit.py` — `SecurityAuditWorkflow` and subagent definitions
- `src/attune/security/` — `SecretsDetector`, `PIIScrubber`, `AuditLogger`, and related types
- `src/attune/monitoring/` — alert engine and telemetry collection (separate subsystem)

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
