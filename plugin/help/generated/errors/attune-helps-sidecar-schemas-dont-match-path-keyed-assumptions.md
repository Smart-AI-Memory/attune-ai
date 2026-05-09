---
type: error
name: attune-helps-sidecar-schemas-dont-match-path-keyed-assumptions
confidence: Verified
tags: [security, git, python]
source: .claude/CLAUDE.md
---

# Error: attune-help's sidecar schemas don't match path-keyed
  assumptions

## Signature

attune-help's sidecar schemas don't match path-keyed
  assumptions

## Root Cause

`attune_help/templates/summaries.json` is keyed by feature name (`"security-audit"`) — NOT by template path. `cross_links.json` is a nested `{version, stats, links, tag_index, workflow_map}` dict keyed by short IDs like `"com-auth-strategies"`, not paths. Any code trying to wire these as flat `path -> value` maps (e.g. a DirectoryCorpus loader) will silently produce empty summaries / related links. Either write an attune-help-specific schema adapter, or load templates without sidecars and treat the missing metadata as a v-next concern.

## Resolution

1. `attune_help/templates/summaries.json` is keyed by feature name (`"security-audit"`) — NOT by template path

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
