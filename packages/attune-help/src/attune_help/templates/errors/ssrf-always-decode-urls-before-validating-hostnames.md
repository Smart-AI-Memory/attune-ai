---
type: error
name: ssrf-always-decode-urls-before-validating-hostnames
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Error: SSRF: always decode URLs before validating hostnames

## Signature

SSRF: always decode URLs before validating hostnames

## Root Cause

`urllib.parse.urlparse` does NOT decode percent-encoded characters. `http://%31%32%37%2e%30%2e%30%2e%31/` parses with hostname `%31%32%37%2e%30%2e%30%2e%31` which bypasses blocklist checks for `127.0.0.1`. Always `urllib.parse.unquote(url)` before parsing and validating.

## Resolution

1. Always `urllib.parse.unquote(url)` before parsing and validating

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: SSRF: always decode URLs before validating hostnames
