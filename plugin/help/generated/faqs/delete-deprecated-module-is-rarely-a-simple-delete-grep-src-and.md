---
type: faq
name: delete-deprecated-module-is-rarely-a-simple-delete-grep-src-and
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about "Delete deprecated module" is rarely a simple delete — grep src/ AND tests/ first?

## Answer

the in-repo `attune.help.generator` 3-depth generator looked like dead code on first glance but had 3 live source consumers (MCP `help_update` handler, `help/maintenance.py`, `help/engine.py`) plus multiple test imports. A straight `rm` would have broken the `help_update` MCP tool.

```
attune.help.generator
```

## Related Topics
- **Error**: Detailed error: "Delete deprecated module" is rarely a simple
  delete — grep src/ AND tests/ first
