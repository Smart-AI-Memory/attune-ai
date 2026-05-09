---
type: error
name: uv-run-pip-audit-runs-the-pyenv-shim-not-the-venv
confidence: Verified
tags: [security, packaging]
source: .claude/CLAUDE.md
---

# Error: `uv run pip-audit` runs the pyenv shim, not the venv

## Signature

`uv run pip-audit` runs the pyenv shim, not the venv

## Root Cause

The pyenv `pip-audit` shim takes precedence on PATH, so `uv run pip-audit` audits whatever Python pyenv points at — not `.venv/`. Symptom: bumping a dep in the venv (verified with `uv pip show`) doesn't change the pip-audit output.

## Resolution

1. install pip-audit *into* the venv with `.venv/bin/python -m pip install pip-audit` and run `.venv/bin/python -m pip_audit`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
