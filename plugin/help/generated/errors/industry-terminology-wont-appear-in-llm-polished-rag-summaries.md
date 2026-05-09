---
type: error
name: industry-terminology-wont-appear-in-llm-polished-rag-summaries
confidence: Verified
tags: [testing, security, packaging]
source: .claude/CLAUDE.md
---

# Error: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms

## Signature

Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms

## Root Cause

When polishing a security-audit summary from the template body, the LLM generated "hardcoded secrets, SQL injection, path traversal" (grounded in the body) but missed "CVE", "OWASP", "pen test", "backdoor" — industry terms that don't appear in the body but are exactly how users phrase queries. Empirical: the security-audit fixture prototype hit 72% P@1 but missed these specific queries; a 5-line prompt addendum ("include domain terminology commonly used in the industry even if it doesn't appear in the template body, as long as it's a genuine synonym for what the template describes") would close most of them. Pattern: for any RAG polish pipeline over a technical corpus, explicitly enumerate the industry vocabulary in the prompt — the grounded-in-body rule alone leaves queries on the table.

## Resolution

1. When polishing a security-audit summary from the template body, the LLM generated "hardcoded secrets, SQL injection, path traversal" (grounded in the body) but missed "CVE", "OWASP", "pen test", "backdoor" — industry terms that don't appear in the body but are exactly how users phrase queries

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms
- Tip: Best practice: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms
- Task: Update test mocks and assertions
