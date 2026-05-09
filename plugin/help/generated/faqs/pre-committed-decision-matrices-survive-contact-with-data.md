---
type: faq
name: pre-committed-decision-matrices-survive-contact-with-data
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pre-committed decision matrices survive contact with data?

## Answer

the fastembed "if Golden P@1 ≥ 70%, defer" matrix was written into `docs/rag/embeddings-decision-2026-04-17.md` BEFORE running Phase 2.5c. When the data came in at 73.3%, there was zero temptation to move the goalpost — the matrix routed the decision cleanly.

```
docs/rag/embeddings-decision-2026-04-17.md
```

## Related Topics
- **Error**: Detailed error: Pre-committed decision matrices survive contact
  with data
