---
type: error
name: mutual-competition-between-polished-rag-features-is-real-and
confidence: Verified
tags: [testing, security, git, packaging]
source: .claude/CLAUDE.md
---

# Error: Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap

## Signature

Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap

## Root Cause

In attune-help 0.7.0, polishing bug-predict's summary in isolation got 76% P@1 on its fixtures. Polishing all 26 features with the same pipeline dropped bug-predict to 44% because competing features (security-audit, code-quality, error-handling-design) now also had polished summaries and stole its queries on shared vocabulary ("eval", "exception", "injection"). Adding per-feature differentiation hints (USP statements describing what each feature uniquely does vs adjacent features) recovered bug-predict to 60% but regressed spec from 44% → 28% because spec is structurally the superset of planning and no prompt engineering dislodges the inclusion. Lesson: when two features genuinely overlap, fix at the **fixture level** (narrow the query set so queries target only what's unique to that feature) or at the **feature level** (merge the features), not at the prompt level.

## Resolution

1. Adding per-feature differentiation hints (USP statements describing what each feature uniquely does vs adjacent features) recovered bug-predict to 60% but regressed spec from 44% → 28% because spec is structurally the superset of planning and no prompt engineering dislodges the inclusion

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap
- Task: Update test mocks and assertions
