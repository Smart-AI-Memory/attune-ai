---
type: warning
name: mutual-competition-between-polished-rag-features-is-real-and
confidence: Verified
tags: [testing, security, git, packaging]
source: .claude/CLAUDE.md
---

# Warning: Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap

## Condition

In attune-help 0.7.0, polishing bug-predict's summary in isolation got 76% P@1 on its fixtures

## Risk

In attune-help 0.7.0, polishing bug-predict's summary in isolation got 76% P@1 on its fixtures

## Mitigation

1. Adding per-feature differentiation hints (USP statements describing what each feature uniquely does vs adjacent features) recovered bug-predict to 60% but regressed spec from 44% → 28% because spec is structurally the superset of planning and no prompt engineering dislodges the inclusion

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap
