---
type: error
name: semantic-cache-70-hit-rate-claim-was-unmeasured
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Semantic cache 70% hit rate claim was unmeasured

## Signature

Semantic cache 70% hit rate claim was unmeasured

## Root Cause

Telemetry data (`~/.attune/telemetry/usage.jsonl`, 17,264 requests) showed 0.2% hit rate and $0.26 saved out of $72. The 0.95 similarity threshold and non-repetitive workflow prompts (unique file paths, timestamps, code snippets) meant near-matches almost never fired. Always verify performance claims against actual telemetry before documenting them.

## Resolution

1. Always verify performance claims against actual telemetry before documenting them

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Semantic cache 70% hit rate claim was unmeasured
- Tip: Best practice: Semantic cache 70% hit rate claim was unmeasured
