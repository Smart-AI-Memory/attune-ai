---
type: warning
name: ssrf-strip-ipv6-zone-ids-before-ip-validation
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Warning: SSRF: strip IPv6 zone IDs before IP validation

## Condition

IPv6 zone IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()` checks because the `%` suffix makes parsing fail or return unexpected results

## Risk

IPv6 zone IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()` checks because the `%` suffix makes parsing fail or return unexpected results

## Mitigation

1. IPv6 zone IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()` checks because the `%` suffix makes parsing fail or return unexpected results

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: SSRF: strip IPv6 zone IDs before IP validation
