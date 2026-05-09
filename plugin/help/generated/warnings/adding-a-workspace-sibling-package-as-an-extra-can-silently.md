---
type: warning
name: adding-a-workspace-sibling-package-as-an-extra-can-silently
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins

## Condition

attune-ai has attune-rag 0.1.4 (transitively requires `attune-help>=0.7.0`)

## Risk

No warning, no conflict error, just a silent downgrade

## Mitigation

1. Adding an `[author]` extra that pulls in attune-author 0.4.0 (which caps `attune-help<0.6`) caused uv to resolve attune-help back DOWN to 0.5.1 — the most restrictive cap wins, not the newest available version

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins
