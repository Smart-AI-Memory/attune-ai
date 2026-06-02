---
type: faq
name: security-audit-faq
feature: security-audit
depth: faq
generated_at: 2026-06-02T10:56:02.703460+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Security Audit FAQ

## What does the security audit do?

It scans your codebase for vulnerabilities — `eval()`/`exec()` usage, path traversal, hardcoded secrets, SQL and command injection, SSRF, and weak cryptography — then produces a severity-grouped report with actionable remediation steps.

## When should I run a security audit?

Run it before releasing a new version, after adding code that handles files or user input, when pulling in a new dependency, or as a CI gate on pull requests. The `SecurityAuditWorkflow` coordinates four specialized subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner`) and synthesizes their findings into a single report.

## How do I run it from the command line?

```
attune workflow run security-audit --path "src/"
```

Results are grouped by severity (CRITICAL, HIGH, MEDIUM, LOW) and include file paths, line numbers, and prioritized fix suggestions.

## How do I run it from the SDK?

Instantiate `SecurityAuditWorkflow` from `workflows.security_audit` and call `execute()`:

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

result = SecurityAuditWorkflow().execute(path="src/")
```

You can pass `system_prompt_suffix` to append instructions to the default auditor prompt.

## What vulnerabilities does it find?

| Category | Examples |
|---|---|
| Code injection | `eval()`, `exec()`, `compile()` on untrusted input |
| Path traversal | File operations without path validation |
| Hardcoded secrets | API keys, tokens, and passwords in source |
| SQL/command injection | String concatenation in queries or shell commands |
| SSRF | HTTP requests to user-controlled URLs |
| Weak cryptography | MD5/SHA1 for security purposes, hardcoded IVs |

## What does the output look like?

The report has three sections: a **Summary** with an overall security score (0–100) and an executive overview, a **Security** section with findings organized by severity, and a **Suggestions** section with remediation steps ordered by priority and estimated effort.

## Can I detect secrets programmatically without running the full workflow?

Yes. Use `detect_secrets` from the `security` module, which is part of the public API alongside `SecretsDetector`, `SecretType`, and `SecretDetection`.

## Can I set up alerts when security-related metrics cross a threshold?

Yes. Use `AlertEngine.add_alert()` to configure a threshold on any `AlertMetric`, then call `AlertEngine.check_and_trigger()` (or run `attune alerts watch`) to fire notifications through your chosen `AlertChannel`. See the alert engine docs for the full setup.

## How do I debug a failed audit run?

Run the related tests first:

```
pytest -k "security-audit" -v
```

If the tests pass but the workflow still fails, check that the path you passed to `execute()` is accessible and that `_validate_file_path` (exported from the `security` module) accepts it. For notification delivery failures, call `MultiBackend.get_failed_backends()` to identify which backend is rejecting records.

## Where are the source files?

- `src/attune/workflows/security_audit.py` — `SecurityAuditWorkflow`
- `src/attune/security/` — `AuditLogger`, `SecretsDetector`, `PIIScrubber`, and related classes
- `src/attune/monitoring/` — alert engine, notification delivery, and telemetry backends

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
