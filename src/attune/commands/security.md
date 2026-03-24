---
name: security
description: "Scan code for security vulnerabilities — eval/exec, path traversal, secrets, injection."
argument-hint: "<path or directory to scan>"
---

Run a security audit on `$ARGUMENTS`.

If no path was provided, ask the user what to scan.

Use `uv run attune workflow run security-audit --path <target>`
to execute. Scope the audit with AskUserQuestion first:
target path, focus areas (OWASP top 10, path traversal,
secrets, or all).
