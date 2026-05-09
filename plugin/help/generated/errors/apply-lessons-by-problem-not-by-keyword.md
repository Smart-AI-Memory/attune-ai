---
type: error
name: apply-lessons-by-problem-not-by-keyword
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Apply lessons by problem, not by keyword

## Signature

Apply lessons by problem, not by keyword

## Root Cause

The `sentence-transformers removed — 0.4% savings, 420MB` lesson is about **semantic caching** (match similar queries to cached responses). It does NOT generalize to **RAG retrieval** (match queries to documents). The ROI profiles differ — attune workflow prompts are mostly unique (file paths, code snippets) so caching misses; retrieval ROI depends on how often semantic similarity beats keyword overlap, which is much higher. The install-size half of the lesson (420MB) IS transferable and correctly rules out `sentence-transformers` for any use case with a <50MB gate. When citing prior lessons, check whether you're invoking the mechanism or the specific problem.

## Resolution

1. The `sentence-transformers removed — 0.4% savings, 420MB` lesson is about **semantic caching** (match similar queries to cached responses)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Apply lessons by problem, not by keyword
