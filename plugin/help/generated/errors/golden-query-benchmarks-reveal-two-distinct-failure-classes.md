---
type: error
name: golden-query-benchmarks-reveal-two-distinct-failure-classes
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Golden-query benchmarks reveal two distinct
  failure classes that need different fixes

## Signature

Golden-query benchmarks reveal two distinct
  failure classes that need different fixes

## Root Cause

(1) **corpus gaps** — query doesn't appear in any feature's name/desc/tags. One-line manifest edit (add tag, paraphrase description) closes these. (2) **structural ambiguity** — query legitimately matches multiple features (e.g. "review" applies to both code-quality AND deep-review; "bugs" applies to both code-quality AND bug-predict). No manifest edit or resolver improvement resolves class (2) because the ambiguity lives in the tag/description vocabulary, not in the cascade ordering. The correct responses to class (2) are: (a) accept the XFAIL as "this is genuinely ambiguous, user needs disambiguation UI," (b) change the resolver contract to return a list of candidates, or (c) strip the shared tag from one feature (changes semantics). Don't mistake (2) for a corpus problem and keep adding tags — you can't fix a shared-tag collision with more tags.

## Resolution

1. (1) **corpus gaps** — query doesn't appear in any feature's name/desc/tags

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Golden-query benchmarks reveal two distinct
  failure classes that need different fixes
- Tip: Best practice: Golden-query benchmarks reveal two distinct
  failure classes that need different fixes
