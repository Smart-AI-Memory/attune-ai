---
type: error
name: selective-hook-skip-with-skip-hookname-is-not-the-same-as-no
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Selective hook skip with `SKIP=hookname` is not the same
  as `--no-verify`

## Signature

Selective hook skip with `SKIP=hookname` is not the same
  as `--no-verify`

## Root Cause

`SKIP=check-docs-freshness git commit …` runs every other pre-commit hook (black, ruff, bandit, detect-secrets, etc.) and skips only the named one. This is defensible when one specific hook fails on state orthogonal to the commit (e.g., docs-freshness flagging pre-existing template staleness when the commit is unrelated). `--no-verify` skips ALL hooks and is what the rules forbid; `SKIP=` is the surgical alternative.

## Resolution

1. `SKIP=check-docs-freshness git commit …` runs every other pre-commit hook (black, ruff, bandit, detect-secrets, etc.) and skips only the named one

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
