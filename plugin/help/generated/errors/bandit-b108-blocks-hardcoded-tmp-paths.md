---
type: error
name: bandit-b108-blocks-hardcoded-tmp-paths
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: Bandit B108 blocks hardcoded `/tmp` paths

## Signature

Bandit B108 blocks hardcoded `/tmp` paths

## Root Cause

Using a literal `/tmp/...` string in `subprocess.run` or `open()` triggers bandit B108 (insecure temp file usage).

## Resolution

1. use `tempfile.TemporaryDirectory(prefix="...")` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Bandit B108 blocks hardcoded `/tmp` paths
