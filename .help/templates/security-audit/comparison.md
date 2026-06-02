---
type: comparison
name: security-audit-comparison
feature: security-audit
depth: comparison
generated_at: 2026-06-02T10:56:02.715269+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Comparison: Security Audit approaches

## Context

Attune offers two ways to scan your codebase for security vulnerabilities — eval/exec usage, path traversal, hardcoded secrets, and injection risks. Choosing the right one depends on how much orchestration you need and where you want results delivered.

| | `SecurityAuditWorkflow` (SDK) | `/security-audit` skill (CLI) |
|---|---|---|
| **Entry point** | `SecurityAuditWorkflow.execute(**kwargs)` | `attune workflow run security-audit --path "src/"` |
| **Subagents** | Four specialized subagents: `vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner` | Single-pass pattern scan |
| **Output** | Unified report: Summary, Security (by severity), Suggestions (by priority) | Severity-grouped findings with CWE identifiers in your terminal |
| **Depth** | Multi-pass; maps findings to OWASP categories with fix suggestions | Surface-to-standard scan; ~30 s (quick) to ~2 min (standard) |
| **Customizable prompt** | Yes — via `system_prompt_suffix` in `__init__` | No |
| **Secrets detection** | `secret-detector` subagent backed by `SecretsDetector` / `detect_secrets` | Yes, as part of pattern matching |
| **PII detection** | Available via `PIIScrubber` / `PIIDetection` in `security` module | Not exposed |
| **Integration with alerts** | Pair with `AlertEngine` to trigger on findings | Not directly wired to alert system |
| **Best for** | Pre-release audits, CI gates, deep OWASP reviews | Quick scans during development, ad-hoc checks in Claude Code |

## Feature-by-feature breakdown

### Vulnerability coverage

Both approaches detect the same core vulnerability classes — code injection (`eval`, `exec`, `compile`), path traversal, hardcoded secrets, SQL/command injection, SSRF, and weak cryptography. The `SecurityAuditWorkflow` assigns each class to a dedicated subagent, so `auth-reviewer` focuses exclusively on authentication logic while `vuln-scanner` handles injection patterns. The CLI skill applies all checks in a single pass.

### Depth and report structure

`SecurityAuditWorkflow` synthesizes subagent output into three sections: a scored executive summary (0–100 security score), consolidated findings organized by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and prioritized remediation steps with effort estimates. The CLI skill produces severity-grouped findings with CWE identifiers — useful for a quick triage but without the remediation roadmap.

### Secret and PII handling

The `security` module exposes `SecretsDetector`, `SecretType`, `PIIScrubber`, and `PIIDetection` directly. `SecurityAuditWorkflow` routes secret detection through its dedicated `secret-detector` subagent. If you need to scrub PII from telemetry logs *before* they reach a `TelemetryBackend`, use `PIIScrubber` independently — neither audit surface handles that automatically.

### Alert integration

Neither audit surface fires alerts on its own. If you want threshold-based notifications when findings exceed a severity level, wire `AlertEngine.add_alert()` with an appropriate `AlertMetric` and `AlertSeverity`, then call `AlertEngine.check_and_trigger()` after a workflow run. Notifications can be delivered via `deliver_webhook`, `deliver_email`, or `deliver_stdout`.

## Use X when…

**Use `SecurityAuditWorkflow`** when you need a comprehensive audit with actionable remediation steps — before releasing a new version, after adding code that handles files or user input, when integrating a new dependency, or as a CI gate on pull requests. Its four-subagent architecture produces findings that cite file paths and line numbers, and its `system_prompt_suffix` parameter lets you restrict scope (for example, to a single package or vulnerability class).

**Use the `/security-audit` skill or `attune workflow run security-audit`** when you want a fast, no-configuration scan during active development. A quick scan takes roughly 30 seconds and delivers results directly in your terminal or Claude Code conversation — ideal for a sanity check before committing, not for a pre-release sign-off.

**Use the `security` module directly** (`SecretsDetector`, `PIIScrubber`, `AuditLogger`) when you need to integrate detection into your own pipeline — for example, scrubbing secrets from telemetry records before they reach `MultiBackend` or `OTELBackend`.

The `SecurityAuditWorkflow` is the stronger choice for thoroughness; the CLI skill wins on speed and zero setup. If you are unsure, run the CLI skill first — if it surfaces anything in the `CRITICAL` or `HIGH` range, follow up with `SecurityAuditWorkflow` for the full remediation plan.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
