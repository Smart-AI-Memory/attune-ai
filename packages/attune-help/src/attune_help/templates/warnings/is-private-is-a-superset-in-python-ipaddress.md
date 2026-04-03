---
type: warning
name: is-private-is-a-superset-in-python-ipaddress
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: `is_private` is a superset in Python `ipaddress`

## Condition

Loopback (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified (`0.0.0.0`) all have `is_private=True`

## Risk

When checking IP safety, test specific attributes (`is_loopback`, `is_link_local`, etc.) before `is_private` so error messages are precise

## Mitigation

1. Loopback (`127.0.0.1`), link-local (`169.254.x.x`), and unspecified (`0.0.0.0`) all have `is_private=True`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `is_private` is a superset in Python `ipaddress`
