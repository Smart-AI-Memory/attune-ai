---
type: faq
name: never-paste-pypi-tokens-into-chat-or-logs
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: What is the best practice for never paste PyPI tokens into chat or logs?

## Answer

Tokens pasted into a conversation are permanently exposed. If a token is exposed, revoke it immediately at pypi.org/manage/account/token.

**How to fix:**
- Always use environment variables set in a separate terminal, or use trusted publishing (OIDC) to avoid tokens altogether

## Related Topics
- **Error**: Detailed error: Never paste PyPI tokens into chat or logs
