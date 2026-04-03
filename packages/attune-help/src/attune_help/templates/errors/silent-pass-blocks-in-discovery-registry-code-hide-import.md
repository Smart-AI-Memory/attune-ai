---
type: error
name: silent-pass-blocks-in-discovery-registry-code-hide-import
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Error: Silent `pass` blocks in discovery/registry code hide
  import failures

## Signature

ImportError

## Root Cause

Workflow discovery had 6 silent `pass` blocks that swallowed `ImportError`/`AttributeError`. When a workflow disappeared from `attune workflow list`, there was no diagnostic output at any log level. Always use `logger.warning()` in discovery paths so `--verbose` or log inspection can surface the root cause.

## Resolution

1. Always use `logger.warning()` in discovery paths so `--verbose` or log inspection can surface the root cause

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Silent `pass` blocks in discovery/registry code hide
  import failures
