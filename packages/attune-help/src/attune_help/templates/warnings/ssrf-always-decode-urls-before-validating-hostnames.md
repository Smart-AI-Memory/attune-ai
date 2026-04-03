---
type: warning
name: ssrf-always-decode-urls-before-validating-hostnames
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Warning: SSRF: always decode URLs before validating hostnames

## Condition

`urllib.parse.urlparse` does NOT decode percent-encoded characters

## Risk

`http://%31%32%37%2e%30%2e%30%2e%31/` parses with hostname `%31%32%37%2e%30%2e%30%2e%31` which bypasses blocklist checks for `127.0.0.1`

## Mitigation

1. Always `urllib.parse.unquote(url)` before parsing and validating

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: SSRF: always decode URLs before validating hostnames
