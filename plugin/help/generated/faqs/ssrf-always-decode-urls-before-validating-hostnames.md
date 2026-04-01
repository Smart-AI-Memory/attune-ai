---
type: faq
name: ssrf-always-decode-urls-before-validating-hostnames
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about SSRF: always decode URLs before validating hostnames?

## Answer

`urllib.parse.urlparse` does NOT decode percent-encoded characters. `http://%31%32%37%2e%30%2e%30%2e%31/` parses with hostname `%31%32%37%2e%30%2e%30%2e%31` which bypasses blocklist checks for `127.0.0.1`.

**How to fix:**
- Always `urllib.parse.unquote(url)` before parsing and validating

```
urllib.parse.urlparse
```

## Related Topics
- **Error**: Detailed error: SSRF: always decode URLs before validating hostnames
