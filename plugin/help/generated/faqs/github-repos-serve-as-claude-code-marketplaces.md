---
name: github-repos-serve-as-claude-code-marketplaces
source: .claude/CLAUDE.md
summary: This template explains how to configure a GitHub repository as a Claude Code
  plugin marketplace and how users can install plugins from it.
tags:
- git
- claude-code
type: faq
---

# FAQ: How do GitHub repos serve as Claude Code marketplaces?

## Answer

GitHub repositories can function as Claude Code plugin marketplaces. To set one up, add a `.claude-plugin/marketplace.json` file at the repo root with a `source` field pointing to the plugin subdirectory (for example, `"./plugin"`).

> **Note:** The marketplace clones from the default branch. Changes must be merged to `main` before users can see them.

### Installing a plugin from a marketplace

Users install a plugin with two commands:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

### Expected file structure

```
.claude-plugin/marketplace.json
```

## Related Topics

- [GitHub repos serve as Claude Code marketplaces](/errors/github-repos-marketplace)
