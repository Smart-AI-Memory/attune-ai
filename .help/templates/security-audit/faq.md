---
type: faq
feature: security-audit
depth: faq
generated_at: 2026-04-19T18:44:29.301094+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security Audit FAQ

## What is security audit?

Security audit scans your code for vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks. It returns severity-grouped findings with CWE identifiers.

## When should I use security audit?

Use security audit before deploying code, after adding new dependencies, or when reviewing pull requests. Run it regularly as part of your CI/CD pipeline to catch security issues early.

## How do I run a security audit?

You can run it as a workflow command or use the Claude Code skill:

```bash
attune workflow run security-audit --path "src/"
```

Or in Claude Code:
```
/security-audit src/
```

## What does the output look like?

You get a structured report with a security score and findings grouped by severity (Critical, High, Medium, Low). Each finding includes the file path, line number, description, and CWE identifier.

## Can I scan specific files or directories?

Yes. You can scan a single file (`/security-audit src/auth.py`), a directory (`/security-audit src/`), or your entire project (`/security-audit .`).

## How do I fix the issues it finds?

After reviewing the results, ask for fixes directly: "fix the critical findings" will generate patches. You can also ask for security tests: "write tests for the flagged files" to prevent regressions.

## What security issues does it detect?

The audit checks for eval/exec usage, path traversal vulnerabilities, hardcoded secrets, SQL injection, command injection, SSRF risks, and other common security patterns based on OWASP guidelines.

## How do I debug security audit issues?

Run the related tests first: `pytest -k "security-audit" -v`. If tests pass but your audit fails, check that your file paths are valid and accessible.

## Where are the source files?

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
