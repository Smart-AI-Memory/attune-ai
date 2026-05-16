---
type: quickstart
name: security-audit-quickstart
feature: security-audit
depth: quickstart
generated_at: 2026-05-16T06:19:45.815255+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Quickstart: Run a security audit

Scan your codebase for vulnerabilities — hardcoded secrets, injection risks, path traversal, and authentication flaws — using four specialized subagents.

```
attune workflow run security-audit --path "src/"
```

**Result:** A unified report with an overall security score, findings grouped by severity (CRITICAL, HIGH, MEDIUM, LOW), and prioritized remediation steps with estimated effort.

## Prerequisites

- `attune` installed and your project available locally
- The codebase you want to scan accessible at a known path

## Steps

1. **Run the audit.** Point `--path` at the directory you want to scan:

   ```
   attune workflow run security-audit --path "src/"
   ```

2. **Review the report.** The output contains three sections:
   - **Summary** — a 0–100 security score and a brief executive summary
   - **Security** — consolidated findings from all four subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`), sorted by severity
   - **Suggestions** — actionable remediation steps ordered by priority

3. **Address critical findings first.** Each finding cites file paths and line numbers, so you can navigate directly to the affected code.

## Expected output

```
## Summary
Security score: 74/100
Two hardcoded credentials and one path-traversal risk require immediate attention.

## Security
### CRITICAL
- src/api/auth.py:42 — Hardcoded API key detected (secret-detector)
...

## Suggestions
1. Rotate and externalize credentials in src/api/auth.py (effort: low)
...
```

**Next:** Fix critical issues, then run `attune workflow run test-gen` to validate your changes.
