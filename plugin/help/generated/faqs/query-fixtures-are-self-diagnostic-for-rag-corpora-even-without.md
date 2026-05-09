---
type: faq
name: query-fixtures-are-self-diagnostic-for-rag-corpora-even-without
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about query fixtures are self-diagnostic for RAG corpora even without wiring them into the retriever?

## Answer

Writing ~25 hand-crafted queries for one feature and running them through the current pipeline exposed which keywords are *missing from corpus entries* without any code changes. For attune-rag bug-predict, this revealed that patterns the feature literally scans for ("race conditions", "memory leaks", "subprocess injection") appear nowhere in its summary or top-of-body prose — they live in error- filename noise that the retriever penalizes.

```
target_keywords
```

## Related Topics
- **Error**: Detailed error: Query fixtures are self-diagnostic for RAG corpora
  even without wiring them into the retriever
