---
type: warning
name: silent-pass-blocks-in-discovery-registry-code-hide-import
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Warning: Silent `pass` blocks in discovery/registry code hide
  import failures

## Condition

Workflow discovery had 6 silent `pass` blocks that swallowed `ImportError`/`AttributeError`

## Risk

Workflow discovery had 6 silent `pass` blocks that swallowed `ImportError`/`AttributeError`

## Mitigation

1. Always use `logger.warning()` in discovery paths so `--verbose` or log inspection can surface the root cause

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Silent `pass` blocks in discovery/registry code hide
  import failures
