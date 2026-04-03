---
type: concept
name: tool-security-audit
tags: [security, skill, workflow]
source: plugin/skills/security-audit/SKILL.md
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

## When you'd use it

Run a security audit before releasing a new version,
after adding code that handles files or user input, when
pulling in a new dependency, or as a CI gate on pull
requests. A quick scan takes under a minute. A deep
review takes longer but maps findings to OWASP
categories.

## How deep it goes

| Depth | Time | What you get |
|-------|------|-------------|
| **Quick** | ~30s | Surface scan — eval/exec, obvious secrets |
| **Standard** | ~2 min | Full pattern matching with severity ratings |
| **Deep** | ~5 min | Multi-pass review with OWASP mapping and fix suggestions |

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is code quality?"** for a broader code review
- Say **"tell me about bug prediction"** to predict where failures happen
