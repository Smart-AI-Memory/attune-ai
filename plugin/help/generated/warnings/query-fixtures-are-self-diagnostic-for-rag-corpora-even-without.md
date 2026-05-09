---
type: warning
name: query-fixtures-are-self-diagnostic-for-rag-corpora-even-without
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Warning: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever

## Condition

Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes

## Risk

Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes

## Mitigation

1. Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever
