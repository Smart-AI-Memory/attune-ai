---
type: error
name: never-paste-pypi-tokens-into-chat-or-logs
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: Never paste PyPI tokens into chat or logs

## Signature

Never paste PyPI tokens into chat or logs

## Root Cause

Tokens pasted into a conversation are permanently exposed. Always use environment variables set in a separate terminal, or use trusted publishing (OIDC) to avoid tokens altogether. If a token is exposed, revoke it immediately at pypi.org/manage/account/token.

## Resolution

1. Always use environment variables set in a separate terminal, or use trusted publishing (OIDC) to avoid tokens altogether

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Never paste PyPI tokens into chat or logs
- Tip: Best practice: Never paste PyPI tokens into chat or logs
