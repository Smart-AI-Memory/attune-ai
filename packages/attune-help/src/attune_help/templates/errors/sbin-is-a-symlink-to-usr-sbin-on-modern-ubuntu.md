---
type: error
name: sbin-is-a-symlink-to-usr-sbin-on-modern-ubuntu
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu

## Signature

`/sbin` is a symlink to `/usr/sbin` on modern Ubuntu

## Root Cause

`Path("/sbin/init").resolve()` does NOT follow the `/sbin` symlink when the target file doesn't exist (Python 3.10+ `strict=False`). Tests asserting that `/sbin/...` is blocked by path validation fail on Ubuntu CI because the resolved path stays as `/sbin/init` which doesn't match the `/usr/sbin` entry in the blocklist. Use `/usr/sbin/...` directly in tests.

## Resolution

1. Use `/usr/sbin/...` directly in tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu
- Task: Update test mocks and assertions
