---
type: warning
name: attune-helps-sidecar-schemas-dont-match-path-keyed-assumptions
confidence: Verified
tags: [security, git, python]
source: .claude/CLAUDE.md
---

# Warning: attune-help's sidecar schemas don't match path-keyed
  assumptions

## Condition

`attune_help/templates/summaries.json` is keyed by feature name (`"security-audit"`) — NOT by template path

## Risk

a DirectoryCorpus loader) will silently produce empty summaries / related links

## Mitigation

1. `attune_help/templates/summaries.json` is keyed by feature name (`"security-audit"`) — NOT by template path

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: attune-help's sidecar schemas don't match path-keyed
  assumptions
