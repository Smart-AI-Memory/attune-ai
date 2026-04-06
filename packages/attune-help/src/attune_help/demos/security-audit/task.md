---
feature: security-audit
depth: task
generated_at: "2026-04-05T00:00:00+00:00"
source_hash: demo
status: demo
---

# How to Run a Security Audit

## Quick start

Point the scanner at a directory and review the results:

```
security-audit src/
```

You'll get a report grouped by severity with file
locations for each finding.

## Choosing what to scan

You can scan a single file, a directory, or your entire
project:

| Target | What it scans |
|--------|---------------|
| `src/auth.py` | One file |
| `src/` | A directory tree |
| `.` | The whole project |

Narrower scopes run faster and produce more focused
results.

## Choosing a focus

By default, the audit checks everything. Narrow the
focus when you know what you're looking for:

- **Secrets detection** — just hardcoded credentials
- **Injection vulnerabilities** — SQL and command injection
- **Dependency audit** — known CVEs in dependencies
- **Full sweep** — everything (default)

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

Each finding includes the file, line number, a short
description, and a CWE identifier where applicable.

## What to do next

After reviewing the results:

- **Fix critical issues first** — these are real attack
  vectors
- **Generate regression tests** — prevent the same
  vulnerability from reappearing
- **Go deeper on one area** — run a focused deep scan on
  the most affected directory
- **Export for CI** — add the scan to your CI pipeline so
  new code is checked automatically
