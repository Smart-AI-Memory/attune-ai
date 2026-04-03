---
type: task
name: use-security-audit
tags: [security, skill, task]
source: plugin/skills/security-audit/SKILL.md
---

# How to Run a Security Audit

## Quick start

The fastest way: just say what you want to scan.

```
scan src/ for security issues
```

Or use the skill directly:

```
/security-audit src/
```

That's it. You'll get a report grouped by severity with
clickable file links.

## Choosing what to scan

You can scan a single file, a directory, or your entire
project:

| Command | What it scans |
|---------|---------------|
| `/security-audit src/auth.py` | One file |
| `/security-audit src/` | A directory tree |
| `/security-audit .` | The whole project |

If you don't specify a path, you'll be asked to choose
one.

## Choosing a focus

By default, the audit checks everything. If you're
looking for something specific, say so:

- "check for hardcoded secrets" — just secrets detection
- "look for injection vulnerabilities" — SQL and command injection
- "scan dependencies for known CVEs" — dependency audit only
- "full sweep" — everything (default)

## Reading the results

Results come back as a table sorted by severity:

```
Security Audit Results
Score: 82/100 | Files: 47 | Issues: 5

Critical
  src/hooks/executor.py:89  — eval() on user input (CWE-95)

High
  src/config.py:203         — Path not validated (CWE-22)
  src/api/webhook.py:45     — URL not checked for SSRF (CWE-918)

Medium
  src/auth/session.py:112   — Broad exception masks errors
  tests/fixtures.py:34      — Hardcoded test credential
```

Each finding includes the file, line number, description,
and CWE identifier. File links are clickable — click to
jump directly to the issue.

## What to do next

After reviewing the results, you have several options:

- **Fix the critical issues** — ask "fix the critical findings" and the audit will generate patches
- **Generate security tests** — ask "write tests for the flagged files" to prevent regressions
- **Go deeper** — ask "deep scan src/auth/" to run a thorough review on a specific area
- **Get the full reference** — say "tell me more" for the complete list of checks and configuration options

## Want to learn more?

- Say **"tell me more"** for the complete reference — every check, configuration, scoring
- Say **"what is security audit?"** to go back to the overview
- Say **"review my code"** to run a code quality review instead
