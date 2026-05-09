---
type: error
name: pytest-lives-in-the-dev-extra-not-developer
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: `pytest` lives in the `dev` extra, not `developer`

## Signature

`pytest` lives in the `dev` extra, not `developer`

## Root Cause

The `developer` extra in `pyproject.toml` does NOT include pytest — that's in the separate `dev` extra. Symptom: `.venv/bin/python -m pytest` exits with `No module named pytest` after `uv sync --extra developer`.

## Resolution

1. sync both with `uv sync --extra dev --extra developer`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
