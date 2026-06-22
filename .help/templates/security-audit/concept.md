---
type: concept
name: security-audit-concept
feature: security-audit
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Security Audit

Security audit is a workflow that scans your codebase for vulnerabilities that are easy to introduce and hard to spot in code review — things like `eval()` on untrusted input, file paths built without validation, API keys committed to source control, and injection risks in queries or shell commands.

## How it works

`SecurityAuditWorkflow` coordinates four specialized subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — each focused on a distinct domain. After all four finish, the workflow synthesizes their output into a single report structured around three sections:

- **Summary** — an overall security score (0–100) and a short executive summary of your security posture
- **Security** — consolidated findings organized by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- **Suggestions** — actionable remediation steps ordered by priority, with estimated effort for each fix

Findings cite file paths and line numbers where possible.

On the security side, the `security` module exposes `SecretsDetector`, `PIIScrubber`, and `AuditLogger` as the underlying detection primitives. `detect_secrets` and `_validate_file_path` are the functions most likely to appear in scan results. `SecurityViolation` and `Severity` carry individual finding details through the pipeline.

## What the scan covers

| Category | What to look for |
|----------|-----------------|
| **Code injection** | `eval()`, `exec()`, and `compile()` on untrusted input |
| **Path traversal** | File operations that don't validate the path first |
| **Hardcoded secrets** | API keys, tokens, and passwords committed to source |
| **SQL/command injection** | String concatenation in queries or shell commands |
| **PII exposure** | Personal data handled without scrubbing (`PIIScrubber`, `PIIPattern`) |
| **Weak cryptography** | MD5/SHA1 for security purposes, hardcoded IVs |

## How security audit relates to monitoring

Security audit findings feed into the broader monitoring system. `AuditEvent` records are what the `AuditLogger` writes; those records can drive `AlertEngine` thresholds. An `AlertConfig` ties a specific `AlertMetric` to a `threshold` float and an `AlertChannel` (webhook, email, or stdout). When `AlertEngine.check_and_trigger()` finds a metric above its threshold, it produces an `AlertEvent` — a snapshot containing `current_value`, `threshold`, `severity`, and `triggered_at` — and delivers it via `deliver_notification`.

The `cooldown_seconds` field on `AlertConfig` (default `3600`) prevents alert storms: once an alert fires, it won't fire again until the cooldown expires.

## Entry points

| Surface | How you reach it |
|---------|-----------------|
| `SecurityAuditWorkflow.execute(**kwargs)` | SDK — run the four-subagent workflow programmatically |
| `attune workflow run security-audit --path "src/"` | CLI — scan a directory and get severity-grouped findings |
| `/security-audit <path>` | Claude Code skill — structured results in your conversation |
| `detect_secrets(...)` | Python API — call the secret-detection primitive directly |
| `AuditLogger` | Python API — write `AuditEvent` records from your own code |
