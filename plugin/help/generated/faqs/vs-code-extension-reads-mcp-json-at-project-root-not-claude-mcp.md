---
type: faq
name: vs-code-extension-reads-mcp-json-at-project-root-not-claude-mcp
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about VS Code extension reads .mcp.json at project root, not .claude/mcp.json?

## Answer

The Claude Code CLI reads `.claude/mcp.json` but the VS Code extension reads `.mcp.json` at the project root. To support both, maintain both files with identical content.

```
.claude/mcp.json
```

## Related Topics
- **Error**: Detailed error: VS Code extension reads `.mcp.json` at project root, not
  `.claude/mcp.json`
