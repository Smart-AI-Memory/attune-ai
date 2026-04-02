---
type: faq
name: ssrf-strip-ipv6-zone-ids-before-ip-validation
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about SSRF: strip IPv6 zone IDs before IP validation?

## Answer

IPv6 zone IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()` checks because the `%` suffix makes parsing fail or return unexpected results. Strip zone IDs with `hostname.split("%")[0]` before any IP validation.

```
fe80::1%25eth0
```

## Related Topics
- **Error**: Detailed error: SSRF: strip IPv6 zone IDs before IP validation
