---
type: warning
name: dist-can-contain-stale-artifacts-after-version-bumps
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Warning: dist/ can contain stale artifacts after version bumps

## Condition

The `dist/` directory is not automatically rebuilt when `pyproject.toml` version changes

## Risk

Ignoring this guidance may cause: dist/ can contain stale artifacts after version bumps

## Mitigation

1. Always run `rm -rf dist/ && uv run python -m build` before publishing and verify `ls dist/` shows the correct version

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: dist/ can contain stale artifacts after version bumps
