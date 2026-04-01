---
type: faq
name: adding-dns-resolution-to-validate-webhook-url-breaks-tests-that
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does adding DNS resolution to _validate_webhook_url breaks tests that pass real hostnames?

## Answer

Any test calling `_validate_webhook_url` with a non-IP hostname (e.g. `example.com`) now needs `@patch("attune.monitoring.validators.socket.getaddrinfo")` to mock DNS resolution.

```
_validate_webhook_url
```

## Related Topics
- **Error**: Detailed error: Adding DNS resolution to `_validate_webhook_url` breaks tests
  that pass real hostnames
