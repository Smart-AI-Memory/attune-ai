---
type: warning
name: pre-committed-decision-matrices-survive-contact-with-data
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: Pre-committed decision matrices survive contact
  with data

## Condition

the fastembed "if Golden P@1 ≥ 70%, defer" matrix was written into `docs/rag/embeddings-decision-2026-04-17.md` BEFORE running Phase 2.5c

## Risk

Ignoring this guidance may cause: Pre-committed decision matrices survive contact
  with data

## Mitigation

1. the fastembed "if Golden P@1 ≥ 70%, defer" matrix was written into `docs/rag/embeddings-decision-2026-04-17.md` BEFORE running Phase 2.5c

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-committed decision matrices survive contact
  with data
