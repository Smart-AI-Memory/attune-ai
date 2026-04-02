---
type: error
name: ssrf-in-webhook-handlers-is-easy-to-miss
confidence: Verified
tags: [security, claude-code]
source: .claude/CLAUDE.md
---

# Error: SSRF in webhook handlers is easy to miss

## Signature

SSRF in webhook handlers is easy to miss

## Root Cause

The `_execute_webhook()` method in `executor.py` accepts arbitrary URLs without IP blocklist, scheme validation, or DNS resolution checks (CWE-918). Webhook endpoints need the same validation rigor as file paths — add `_validate_webhook_url()` alongside `_validate_file_path()`.

## Resolution

1. The `_execute_webhook()` method in `executor.py` accepts arbitrary URLs without IP blocklist, scheme validation, or DNS resolution checks (CWE-918)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
