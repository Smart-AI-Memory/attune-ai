---
type: concept
name: tool-security-audit
tags: [security, skill, workflow]
source: plugin/skills/security-audit/SKILL.md
---

# Security Audit

## What

Scans your codebase for security vulnerabilities including
eval/exec usage (CWE-95), path traversal (CWE-22),
hardcoded secrets, SQL/command injection, and SSRF risks.
Runs at three depth levels: quick scan, standard audit,
and deep review with OWASP mapping.

## Why

Security bugs are the most expensive to fix after release.
A 5-minute scan catches the issues that code review misses
-- eval in test fixtures, unvalidated file paths, secrets
that slipped past .gitignore.

## When to use

- Before any release or version bump
- After adding file I/O, subprocess calls, or user input
- When onboarding a new dependency or third-party code
- As part of a CI gate for pull requests

## What it checks

| Category | Examples |
|----------|----------|
| Code injection | `eval()`, `exec()`, `compile()` |
| Path traversal | Unvalidated `open()`, `Path.write_*` |
| Secrets | API keys, tokens, passwords in source |
| Injection | SQL string concatenation, shell=True |
| SSRF | Unvalidated URLs in HTTP requests |
| Crypto | Weak hashes (MD5/SHA1), hardcoded IVs |

## Related Topics

- **Task**: Use the security-audit skill -- step-by-step
- **Reference**: Skill: security-audit -- full reference
