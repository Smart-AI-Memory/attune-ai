---
type: error
name: adding-dns-resolution-to-validate-webhook-url-breaks-tests-that
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Error: Adding DNS resolution to `_validate_webhook_url` breaks tests
  that pass real hostnames

## Signature

Adding DNS resolution to `_validate_webhook_url` breaks tests
  that pass real hostnames

## Root Cause

Any test calling `_validate_webhook_url` with a non-IP hostname (e.g. `example.com`) now needs `@patch("attune.monitoring.validators.socket.getaddrinfo")` to mock DNS resolution. Grep for all callers when adding network validation to an existing function.

## Resolution

1. Grep for all callers when adding network validation to an existing function

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
