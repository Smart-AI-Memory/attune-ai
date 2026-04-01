---
type: error
name: ruff-parses-pytest-ini-as-python
confidence: Verified
tags: [testing, git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: ruff parses pytest.ini as Python

## Signature

ruff parses pytest.ini as Python

## Root Cause

When committing `pytest.ini` alongside `.py` files, ruff's pre-commit hook tries to parse it as Python and produces syntax errors. Commit `pytest.ini` in a separate commit from Python files so the ruff hook only sees valid Python.

## Resolution

1. When committing `pytest.ini` alongside `.py` files, ruff's pre-commit hook tries to parse it as Python and produces syntax errors

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
