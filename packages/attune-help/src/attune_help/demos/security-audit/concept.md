---
feature: security-audit
depth: concept
generated_at: "2026-04-05T00:00:00+00:00"
source_hash: demo
status: demo
---

# Security Audit

A security audit scans your codebase for vulnerabilities
that are easy to introduce and hard to spot in code
review. It catches the mistakes that slip through when
you're focused on making things work — an `eval()` in a
test fixture, a file path built from user input without
validation, an API key that ended up in source control.

## What it finds

| Category | What to worry about |
|----------|---------------------|
| **Code injection** | `eval()`, `exec()`, and `compile()` on untrusted input |
| **Path traversal** | File operations that don't validate the path first |
| **Hardcoded secrets** | API keys, tokens, and passwords committed to source |
| **SQL/command injection** | String concatenation in queries or shell commands |
| **SSRF** | HTTP requests to URLs controlled by user input |
| **Weak cryptography** | MD5/SHA1 for security purposes, hardcoded IVs |

## Why it matters

These vulnerabilities are common in everyday code —
they're not exotic attacks. A path traversal bug is just
a missing validation call. A hardcoded secret is a
string that should have been an environment variable.
Automated scanning catches these before they reach
production.

## How deep it goes

| Depth | Time | What you get |
|-------|------|-------------|
| **Quick** | ~30s | Surface scan — eval/exec, obvious secrets |
| **Standard** | ~2 min | Full pattern matching with severity ratings |
| **Deep** | ~5 min | Multi-pass review with OWASP mapping and fix suggestions |
