---
type: error
name: is-private-is-a-superset-in-python-ipaddress
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: `is_private` is a superset in Python `ipaddress`

## Signature

`is_private` is a superset in Python `ipaddress`

## Root Cause

Loopback (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified (`0.0.0.0`) all have `is_private=True`. When checking IP safety, test specific attributes (`is_loopback`, `is_link_local`, etc.) before `is_private` so error messages are precise. The same ordering matters in both IP literal checks and DNS resolution checks.

## Resolution

1. Loopback (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified (`0.0.0.0`) all have `is_private=True`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
