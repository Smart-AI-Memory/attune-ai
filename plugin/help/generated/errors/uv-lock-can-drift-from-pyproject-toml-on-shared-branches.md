---
type: error
name: uv-lock-can-drift-from-pyproject-toml-on-shared-branches
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: uv.lock can drift from pyproject.toml on shared branches

## Signature

uv.lock can drift from pyproject.toml on shared branches

## Root Cause

Saw this on origin/main — pyproject.toml had `attune-help>=0.5.1,<0.6` (cap added in PR #152) but uv.lock still showed `>=0.5.1` (no cap). The cap-adding PR didn't re-run `uv lock`, so the lockfile silently went out of sync. Symptom: a stale local working tree change to uv.lock isn't a no-op after `git pull` — it's a real drift fix. Always `uv lock --check` after pulling, and bundle uv.lock fixes with the next reasonable PR rather than treating them as noise.

## Resolution

1. Always `uv lock --check` after pulling, and bundle uv.lock fixes with the next reasonable PR rather than treating them as noise

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: uv.lock can drift from pyproject.toml on shared branches
