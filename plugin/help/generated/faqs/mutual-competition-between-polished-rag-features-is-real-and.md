---
type: faq
name: mutual-competition-between-polished-rag-features-is-real-and
tags: [testing, security, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why mutual competition between polished RAG features is real and structural — differentiation hints help but can't fully resolve feature-boundary overlap?

## Answer

In attune-help 0.7.0, polishing bug-predict's summary in isolation got 76% P@1 on its fixtures. Polishing all 26 features with the same pipeline dropped bug-predict to 44% because competing features (security-audit, code-quality, error-handling-design) now also had polished summaries and stole its queries on shared vocabulary ("eval", "exception", "injection").

## Related Topics
- **Error**: Detailed error: Mutual competition between polished RAG features
  is real and structural — differentiation hints help
  but can't fully resolve feature-boundary overlap
