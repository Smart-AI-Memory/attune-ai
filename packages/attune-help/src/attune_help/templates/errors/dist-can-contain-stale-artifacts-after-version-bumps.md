---
type: error
name: dist-can-contain-stale-artifacts-after-version-bumps
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: dist/ can contain stale artifacts after version bumps

## Signature

dist/ can contain stale artifacts after version bumps

## Root Cause

The `dist/` directory is not automatically rebuilt when `pyproject.toml` version changes. Always run `rm -rf dist/ && uv run python -m build` before publishing and verify `ls dist/` shows the correct version. Publishing stale artifacts uploads the old version to PyPI.

## Resolution

1. Always run `rm -rf dist/ && uv run python -m build` before publishing and verify `ls dist/` shows the correct version

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: dist/ can contain stale artifacts after version bumps
