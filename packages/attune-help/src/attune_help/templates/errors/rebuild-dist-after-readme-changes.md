---
type: error
name: rebuild-dist-after-readme-changes
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: Rebuild dist after README changes

## Signature

Rebuild dist after README changes

## Root Cause

PyPI uses `README.md` as the package description. If you update the README after the initial build, run `rm -rf dist/ && uv run python -m build` again before publishing or PyPI will show the old README.

## Resolution

1. PyPI uses `README.md` as the package description

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Rebuild dist after README changes
