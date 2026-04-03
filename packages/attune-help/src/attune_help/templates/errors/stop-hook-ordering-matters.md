---
type: error
name: stop-hook-ordering-matters
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Stop hook ordering matters

## Signature

Stop hook ordering matters

## Root Cause

When multiple Stop hook groups are configured, run state-saving hooks (exit 0) first and blocking hooks (exit 2) last. A trailing exit-0 hook may override a preceding exit-2 block.

## Resolution

1. When multiple Stop hook groups are configured, run state-saving hooks (exit 0) first and blocking hooks (exit 2) last

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
