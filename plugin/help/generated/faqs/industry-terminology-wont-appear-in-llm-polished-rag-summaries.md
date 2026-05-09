---
type: faq
name: industry-terminology-wont-appear-in-llm-polished-rag-summaries
tags: [testing, security, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why industry terminology won't appear in LLM-polished RAG summaries unless the prompt explicitly invites common domain synonyms?

## Answer

When polishing a security-audit summary from the template body, the LLM generated "hardcoded secrets, SQL injection, path traversal" (grounded in the body) but missed "CVE", "OWASP", "pen test", "backdoor" — industry terms that don't appear in the body but are exactly how users phrase queries. Empirical: the security-audit fixture prototype hit 72% P@1 but missed these specific queries; a 5-line prompt addendum ("include domain terminology commonly used in the industry even if it doesn't appear in the template body, as long as it's a genuine synonym for what the template describes") would close most of them.

## Related Topics
- **Error**: Detailed error: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms
