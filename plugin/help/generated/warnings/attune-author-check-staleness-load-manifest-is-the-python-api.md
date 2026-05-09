---
type: warning
name: attune-author-check-staleness-load-manifest-is-the-python-api
confidence: Verified
tags: [ci, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection

## Condition

the `attune-author status` CLI emits only markdown tables

## Risk

Ignoring this guidance may cause: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection

## Mitigation

1. Use this anywhere automation would otherwise parse the status table (GitHub Actions, SessionStart hooks, pre-commit scripts)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `attune_author.check_staleness` +
  `load_manifest` is the Python API for programmatic
  stale detection
