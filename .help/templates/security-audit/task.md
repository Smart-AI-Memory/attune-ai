---
feature: security-audit
depth: task
generated_at: 2026-04-13T16:53:39.182361+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Work with security audit

Use security audit when you need to identify security vulnerabilities in your codebase through SDK-native analysis with specialized subagents.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/security_audit.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what security audit
   does today before making changes.
   The primary workflow is:
   - `SecurityAuditWorkflow` in `src/attune/workflows/security_audit.py` — SDK-native security audit with four specialized subagents.
   The supporting alert system includes:
   - `alerts()` in `src/attune/monitoring/alerts_cli.py` — Alert management commands for LLM telemetry monitoring.
   - `init()` in `src/attune/monitoring/alerts_cli.py` — Initialize an alert with interactive workflow or CLI flags.
   - `list_cmd()` in `src/attune/monitoring/alerts_cli.py` — List all configured alerts.

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
