---
type: faq
name: attune-helps-sidecar-schemas-dont-match-path-keyed-assumptions
tags: [security, git, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about attune-help's sidecar schemas don't match path-keyed assumptions?

## Answer

`attune_help/templates/summaries.json` is keyed by feature name (`"security-audit"`) — NOT by template path. `cross_links.json` is a nested `{version, stats, links, tag_index, workflow_map}` dict keyed by short IDs like `"com-auth-strategies"`, not paths.

```
attune_help/templates/summaries.json
```

## Related Topics
- **Error**: Detailed error: attune-help's sidecar schemas don't match path-keyed
  assumptions
