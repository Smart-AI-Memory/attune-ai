---
type: error
name: stop-hooks-missing-cd-prefix-inherit-session-cwd
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Stop hooks missing `cd` prefix inherit session cwd

## Signature

Stop hooks missing `cd` prefix inherit session cwd

## Root Cause

Stop hooks without an explicit `cd /abs/path &&` prefix inherit whatever directory Claude Code was started from — which may not be the repo root. Always prefix Stop (and all) hook commands with `cd /Users/patrickroebuck/attune-ai &&` to guarantee the correct working directory regardless of where the session was opened.

## Resolution

1. Always prefix Stop (and all) hook commands with `cd /Users/patrickroebuck/attune-ai &&` to guarantee the correct working directory regardless of where the session was opened

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Stop hooks missing `cd` prefix inherit session cwd
