---
type: faq
name: github-repos-serve-as-claude-code-marketplaces
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about gitHub repos serve as Claude Code marketplaces?

## Answer

Add `.claude-plugin/marketplace.json` at the repo root with a `source` field pointing to the plugin subdirectory (e.g., `"./plugin"`). The marketplace clones from the default branch — changes must be merged to `main` before users see them.

**How to fix:**
- Users install with two commands: `claude plugin marketplace add Smart-AI-Memory/attune-ai` then `claude plugin install attune-ai@attune-ai`

```
.claude-plugin/marketplace.json
```

## Related Topics
- **Error**: Detailed error: GitHub repos serve as Claude Code marketplaces
