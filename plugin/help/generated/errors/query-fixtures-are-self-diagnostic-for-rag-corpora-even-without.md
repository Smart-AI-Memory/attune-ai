---
type: error
name: query-fixtures-are-self-diagnostic-for-rag-corpora-even-without
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Error: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever

## Signature

Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever

## Root Cause

Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes. For attune-rag bug-predict, this revealed that patterns the feature literally scans for ("race conditions", "memory leaks", "subprocess injection") appear nowhere in its summary or top-of-body prose — they live in error- filename noise that the retriever penalizes. Result: 36% P@1 despite the target feature existing, because query language and corpus content don't overlap. Pattern: for any RAG-tuned library, before investing in embeddings or retriever tuning, generate query fixtures per feature and score them. The misses tell you exactly what corpus content to write. Pairs well with an LLM polish pipeline that consumes the fixture keywords as `target_keywords`.

## Resolution

1. Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever
- Tip: Best practice: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever
- Task: Update test mocks and assertions
