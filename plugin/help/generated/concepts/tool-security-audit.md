---
name: tool-security-audit
source: plugin/skills/security-audit/SKILL.md
summary: This template guides developers through using an automated security scanning
  tool that detects common vulnerabilities like code injection, path traversal, hardcoded
  secrets, and SQL injection across three audit depth levels, with recommendations
  for when and how to integrate it into the development workflow.
tags:
- security
- skill
- workflow
type: concept
---

# Security Audit

Scans your codebase for security vulnerabilities including eval/exec usage (CWE-95), path traversal (CWE-22), hardcoded secrets, SQL/command injection, and SSRF risks. Runs at three depth levels: quick scan, standard audit, and deep review with OWASP mapping.

## Why use it

Security bugs are the most expensive to fix after release. A 5-minute scan catches issues that code review misses — eval in test fixtures, unvalidated file paths, secrets that slipped past `.gitignore`.

## When to use it

- Before any release or version bump
- After adding file I/O, subprocess calls, or user input handling
- When onboarding a new dependency or third-party code
- As a CI gate for pull requests

## What it checks

| Category | Examples |
|---|---|
| Code injection | `eval()`, `exec()`, `compile()` |
| Path traversal | Unvalidated `open()`, `Path.write_*` |
| Hardcoded secrets | API keys, tokens, passwords in source |
| SQL/command injection | String-concatenated queries, `shell=True` |
| SSRF | Unvalidated URLs passed to HTTP clients |
| Weak cryptography | MD5/SHA1 hashes, hardcoded IVs |

## Related topics

- **Task**: Use the security-audit skill — step-by-step walkthrough
- **Reference**: security-audit skill — full option and output reference
