---
type: warning
name: industry-terminology-wont-appear-in-llm-polished-rag-summaries
confidence: Verified
tags: [testing, security, packaging]
source: .claude/CLAUDE.md
---

# Warning: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms

## Condition

When polishing a security-audit summary from the template body, the LLM generated "hardcoded secrets, SQL injection, path traversal" (grounded in the body) but missed "CVE", "OWASP", "pen test", "backdoor" — industry terms that don't appear in the body but are exactly how users phrase queries

## Risk

Ignoring this guidance may cause: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms

## Mitigation

1. When polishing a security-audit summary from the template body, the LLM generated "hardcoded secrets, SQL injection, path traversal" (grounded in the body) but missed "CVE", "OWASP", "pen test", "backdoor" — industry terms that don't appear in the body but are exactly how users phrase queries

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Industry terminology won't appear in LLM-polished
  RAG summaries unless the prompt explicitly invites
  common domain synonyms
