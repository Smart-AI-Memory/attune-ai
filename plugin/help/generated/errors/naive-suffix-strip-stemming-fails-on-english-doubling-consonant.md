---
type: error
name: naive-suffix-strip-stemming-fails-on-english-doubling-consonant
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Naive suffix-strip stemming fails on English
  doubling-consonant words

## Signature

Naive suffix-strip stemming fails on English
  doubling-consonant words

## Root Cause

A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator"). But words with doubled consonants before the suffix break: "planning" strips to "planni" (8 − 3 = 5 chars ≥ min), not "plan". So a user query "plan a new feature" against a `concepts/tool-planning.md` target still misses because "plan" and "planni" don't equate. Full Porter/Krovetz stemmers handle this via rules that restore the dropped consonant (`planning → plann → plan`). Going beyond a simple suffix-strip in a zero-dep retriever isn't worth it — the cases that doubling rules fix are exactly the cases semantic embeddings handle naturally. Documented in attune-rag 0.1.1's benchmark plateau at 66.67% P@1.

## Resolution

1. A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator")

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Naive suffix-strip stemming fails on English
  doubling-consonant words
- Tip: Best practice: Naive suffix-strip stemming fails on English
  doubling-consonant words
