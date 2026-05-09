---
type: warning
name: uv-lock-can-drift-from-pyproject-toml-on-shared-branches
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: uv.lock can drift from pyproject.toml on shared branches

## Condition

Saw this on origin/main — pyproject.toml had `attune-help>=0.5.1,<0.6` (cap added in PR #152) but uv.lock still showed `>=0.5.1` (no cap)

## Risk

The cap-adding PR didn't re-run `uv lock`, so the lockfile silently went out of sync

## Mitigation

1. Always `uv lock --check` after pulling, and bundle uv.lock fixes with the next reasonable PR rather than treating them as noise

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: uv.lock can drift from pyproject.toml on shared branches
