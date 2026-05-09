---
type: error
name: handoff-memory-option-b-proposals-are-often-wrong-re-analyze
confidence: Verified
tags: [security, git]
source: .claude/CLAUDE.md
---

# Error: Handoff-memory "Option B" proposals are often
  wrong — re-analyze after Option A

## Signature

Handoff-memory "Option B" proposals are often
  wrong — re-analyze after Option A

## Root Cause

when writing a project memory that sequences work as "do A first, then B if needed," the B framing is usually speculative and hasn't been validated against the actual problem. After completing A, the problem often looks different: either B is no longer needed, or B as originally framed doesn't address the actual remaining cause. The resolver-upgrade handoff said "Option B = aggregate scoring across cascade steps"; after doing A and re-analyzing, the remaining 2 hard queries were shared-tag collisions that aggregate scoring couldn't touch. Lesson: label speculative proposals clearly in memories ("initial theory, validate before implementing") and always re-evaluate from scratch at pickup time.

## Resolution

1. when writing a project memory that sequences work as "do A first, then B if needed," the B framing is usually speculative and hasn't been validated against the actual problem

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Handoff-memory "Option B" proposals are often
  wrong — re-analyze after Option A
