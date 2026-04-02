---
type: faq
name: validate-infrastructure-against-user-value-before-extending
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about validate infrastructure against user value before extending?

## Answer

BEP middleware was well-built (93 tests, clean protocol) but had zero working skills and no integration with CLI workflows — the surface where all user value lives.

**How to fix:**
- Always validate that new infrastructure serves actual users before investing in production hardening

## Related Topics
- **Error**: Detailed error: Validate infrastructure against user value before extending
