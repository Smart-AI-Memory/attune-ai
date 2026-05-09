---
type: faq
name: adding-a-workspace-sibling-package-as-an-extra-can-silently
source: .claude/CLAUDE.md
---

# FAQ: What should I know about adding a workspace-sibling package as an extra can silently downgrade shared transitive deps via most-restrictive-cap-wins?

## Answer

attune-ai has attune-rag 0.1.4 (transitively requires `attune-help>=0.7.0`). Adding an `[author]` extra that pulls in attune-author 0.4.0 (which caps `attune-help<0.6`) caused uv to resolve attune-help back DOWN to 0.5.1 — the most restrictive cap wins, not the newest available version.

```
attune-help>=0.7.0
```

## Related Topics
- **Error**: Detailed error: Adding a workspace-sibling package as an extra can
  silently downgrade shared transitive deps via
  most-restrictive-cap-wins
