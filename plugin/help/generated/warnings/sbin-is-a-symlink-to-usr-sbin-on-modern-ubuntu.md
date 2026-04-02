---
type: warning
name: sbin-is-a-symlink-to-usr-sbin-on-modern-ubuntu
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Warning: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu

## Condition

`Path("/sbin/init").resolve()` does NOT follow the `/sbin` symlink when the target file doesn't exist (Python 3.10+ `strict=False`)

## Risk

Tests asserting that `/sbin/...` is blocked by path validation fail on Ubuntu CI because the resolved path stays as `/sbin/init` which doesn't match the `/usr/sbin` entry in the blocklist

## Mitigation

1. Use `/usr/sbin/...` directly in tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `/sbin` is a symlink to `/usr/sbin` on modern Ubuntu
