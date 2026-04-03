---
type: error
name: ssrf-strip-ipv6-zone-ids-before-ip-validation
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Error: SSRF: strip IPv6 zone IDs before IP validation

## Signature

SSRF: strip IPv6 zone IDs before IP validation

## Root Cause

IPv6 zone IDs (e.g., `fe80::1%25eth0`) can bypass `ipaddress.ip_address()` checks because the `%` suffix makes parsing fail or return unexpected results. Strip zone IDs with `hostname.split("%")[0]` before any IP validation.

## Resolution

1. Strip zone IDs with `hostname.split("%")[0]` before any IP validation

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: SSRF: strip IPv6 zone IDs before IP validation
