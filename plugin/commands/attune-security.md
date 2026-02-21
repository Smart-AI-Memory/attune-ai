---
name: attune-security
description: "Run a security audit on your codebase"
argument-hint: "<path to scan>"
category: workflows
aliases: [asec]
tags: [security, audit, vulnerability, scan]
version: "3.0.0"
---

# attune-security

Quick-access command to run a security audit. Bypasses
the guided flow for when you know what you want.

## Execution

1. If a path argument is provided, use it. Otherwise
   ask: "Which path should I scan?"
2. Call the `security_audit` MCP tool with the path.
3. Present results grouped by severity using the format
   from the security-audit skill.

## Examples

```
/attune-security src/
/attune-security .
/attune-security src/attune/models/
```
