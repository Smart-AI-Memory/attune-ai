---
type: error
name: github-protected-tags-cannot-be-force-updated
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: GitHub protected tags cannot be force-updated

## Signature

GitHub protected tags cannot be force-updated

## Root Cause

Once a tag is pushed, `git push --force` fails if repository rules protect tags. Tag the correct commit before pushing — there's no easy fix after.

## Resolution

1. Once a tag is pushed, `git push --force` fails if repository rules protect tags

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
