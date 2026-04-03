---
type: warning
name: stop-hooks-missing-cd-prefix-inherit-session-cwd
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Stop hooks missing `cd` prefix inherit session cwd

## Condition

Stop hooks without an explicit `cd /abs/path &&` prefix inherit whatever directory Claude Code was started from — which may not be the repo root

## Risk

Ignoring this guidance may cause: Stop hooks missing `cd` prefix inherit session cwd

## Mitigation

1. Always prefix Stop (and all) hook commands with `cd /Users/patrickroebuck/attune-ai &&` to guarantee the correct working directory regardless of where the session was opened

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Stop hooks missing `cd` prefix inherit session cwd
