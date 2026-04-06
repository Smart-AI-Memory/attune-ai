---
feature: security-audit
depth: task
generated_at: 2026-04-06T04:27:15.074186+00:00
source_hash: f3c7ecfc06b88ed07137562d160e3d10e0168c98f92aa060ae8fbd378b2571c4
status: generated
---

# Work with security audit

Run a security audit when you need to scan your codebase for vulnerabilities before deploying or when security compliance requires validation.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/security_audit.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what the SecurityAuditWorkflow
   does today before making changes.
   The primary functions are:
   - `alerts()` in `src/attune/monitoring/alerts_cli.py` — Manage alerts for LLM telemetry monitoring.
   - `init()` in `src/attune/monitoring/alerts_cli.py` — Initialize an alert with interactive workflow or CLI flags.
   - `list_cmd()` in `src/attune/monitoring/alerts_cli.py` — List all configured alerts.
   - `delete()` in `src/attune/monitoring/alerts_cli.py` — Delete an alert by ID.
   - `enable()` in `src/attune/monitoring/alerts_cli.py` — Enable an alert by ID.

2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "security-audit"`.

## Key files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

## Common modifications

Functions you are most likely to modify:

- `alerts()` in `src/attune/monitoring/alerts_cli.py`
- `init()` in `src/attune/monitoring/alerts_cli.py`
- `list_cmd()` in `src/attune/monitoring/alerts_cli.py`
- `delete()` in `src/attune/monitoring/alerts_cli.py`
- `enable()` in `src/attune/monitoring/alerts_cli.py`
- `disable()` in `src/attune/monitoring/alerts_cli.py`
- `watch()` in `src/attune/monitoring/alerts_cli.py`
- `history()` in `src/attune/monitoring/alerts_cli.py`
