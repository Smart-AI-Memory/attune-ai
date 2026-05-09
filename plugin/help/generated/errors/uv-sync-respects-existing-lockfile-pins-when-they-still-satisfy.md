---
type: error
name: uv-sync-respects-existing-lockfile-pins-when-they-still-satisfy
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `uv sync` respects existing lockfile pins when they
  still satisfy widened constraints — cap bumps require
  `uv lock --upgrade-package <name>` to actually
  upgrade

## Signature

`uv sync` respects existing lockfile pins when they
  still satisfy widened constraints — cap bumps require
  `uv lock --upgrade-package <name>` to actually
  upgrade

## Root Cause

bumping `attune-help>=0.5.1,<0.6` to `<0.8` in pyproject.toml and running `uv sync --all-extras` left attune-help at 0.5.1 because 0.5.1 still satisfies `>=0.5.1,<0.8`. The resolver picks the existing pin over a newer available version.

## Resolution

1. after widening a cap, run `uv lock --upgrade-package <name>` (repeatable for multiple packages) to force re-resolution; then `uv sync` installs the newly- resolved versions

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv sync` respects existing lockfile pins when they
  still satisfy widened constraints — cap bumps require
  `uv lock --upgrade-package <name>` to actually
  upgrade
