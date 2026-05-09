---
type: warning
name: naive-suffix-strip-stemming-fails-on-english-doubling-consonant
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Naive suffix-strip stemming fails on English
  doubling-consonant words

## Condition

A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator")

## Risk

A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator")

## Mitigation

1. A simple stemmer that strips suffixes like `-ing`, `-ion`, `-ate`, `-s` correctly matches most singular/plural and verb-form pairs ("bugs"/"bug", "orchestrate"/ "orchestrator")

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Naive suffix-strip stemming fails on English
  doubling-consonant words
