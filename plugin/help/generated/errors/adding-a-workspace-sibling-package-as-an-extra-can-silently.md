---
type: error
name: adding-a-workspace-sibling-package-as-an-extra-can-silently
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins

## Signature

Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins

## Root Cause

attune-ai has attune-rag 0.1.4 (transitively requires `attune-help>=0.7.0`). Adding an `[author]` extra that pulls in attune-author 0.4.0 (which caps `attune-help<0.6`) caused uv to resolve attune-help back DOWN to 0.5.1 — the most restrictive cap wins, not the newest available version. No warning, no conflict error, just a silent downgrade. Lesson: before adding a new sibling package to an extras list, grep that sibling's pyproject.toml for `attune-*` caps and check they admit what your current transitive closure requires. If they don't, bump the sibling's caps and re-release first. Pattern specifically affects this ecosystem where attune-ai / attune-rag / attune-author / attune-help all share attune-help as a transitive dep with sometimes-divergent cap ranges.

## Resolution

1. Adding an `[author]` extra that pulls in attune-author 0.4.0 (which caps `attune-help<0.6`) caused uv to resolve attune-help back DOWN to 0.5.1 — the most restrictive cap wins, not the newest available version

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins
- Tip: Best practice: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins
