---
type: warning
name: never-paste-pypi-tokens-into-chat-or-logs
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Warning: Never paste PyPI tokens into chat or logs

## Condition

Tokens pasted into a conversation are permanently exposed

## Risk

Ignoring this guidance may cause: Never paste PyPI tokens into chat or logs

## Mitigation

1. Always use environment variables set in a separate terminal, or use trusted publishing (OIDC) to avoid tokens altogether

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Never paste PyPI tokens into chat or logs
