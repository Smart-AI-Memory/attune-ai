---
type: warning
name: golden-query-benchmarks-reveal-two-distinct-failure-classes
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Golden-query benchmarks reveal two distinct
  failure classes that need different fixes

## Condition

(1) **corpus gaps** — query doesn't appear in any feature's name/desc/tags

## Risk

"review" applies to both code-quality AND deep-review; "bugs" applies to both code-quality AND bug-predict)

## Mitigation

1. Don't mistake (2) for a corpus problem and keep adding tags — you can't fix a shared-tag collision with more tags

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Golden-query benchmarks reveal two distinct
  failure classes that need different fixes
