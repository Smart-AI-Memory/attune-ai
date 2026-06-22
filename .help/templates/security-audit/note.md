---
type: note
name: security-audit-note
feature: security-audit
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Note: security audit

## Context

The security audit feature scans a codebase for vulnerabilities including `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks. It is available as both a workflow (`SecurityAuditWorkflow`) and a Claude Code skill (`/security-audit`).

## How the workflow is structured

`SecurityAuditWorkflow` (in `workflows/security_audit`) coordinates four specialized subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — and synthesizes their output into a single report. The report is organized into three sections: a **Summary** with an overall security score (0–100), **Security** findings grouped by severity (CRITICAL, HIGH, MEDIUM, LOW), and **Suggestions** with prioritized remediation steps and estimated effort per fix. File paths and line numbers are cited where available.

## What the security package exposes

The `security` package (`security.__init__`) exports the types used throughout scanning and reporting:

- **Detection:** `SecretsDetector`, `SecretDetection`, `SecretType`, `PIIDetection`, `PIIPattern`, `PIIScrubber`, `detect_secrets`
- **Audit logging:** `AuditEvent`, `AuditLogger`
- **Violation modeling:** `SecurityViolation`, `Severity`
- **Utilities:** `_validate_file_path`

## Relationship to the monitoring system

The monitoring system (`monitoring.__init__`, `monitoring.alerts`) is a separate concern — it tracks LLM call telemetry and fires threshold-based alerts via `AlertEngine`. It is not part of the security scan itself. The two systems share the same repository but serve different purposes: `security` finds vulnerabilities in your code; `monitoring` observes the runtime behavior of your agents.

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
