---
type: faq
name: ssrf-in-webhook-handlers-is-easy-to-miss
tags: [security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about SSRF in webhook handlers is easy to miss?

## Answer

The `_execute_webhook()` method in `executor.py` accepts arbitrary URLs without IP blocklist, scheme validation, or DNS resolution checks (CWE-918). Webhook endpoints need the same validation rigor as file paths — add `_validate_webhook_url()` alongside `_validate_file_path()`.

```
_execute_webhook()
```

## Related Topics
- **Error**: Detailed error: SSRF in webhook handlers is easy to miss
