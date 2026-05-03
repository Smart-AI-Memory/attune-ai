---
name: cli-vs-claude-code
source: smartaimemory.com/attune-plugin/
summary: This template compares the two ways to use attune-ai—as a standalone CLI
  tool for automated workflows and CI/CD pipelines, or as Claude Code skills for interactive
  development with codebase context.
tags:
- cli
- claude-code
type: comparison
---

# Comparison: CLI vs Claude Code Usage

There are two ways to use attune-ai: as a standalone CLI or within Claude Code conversations.

| Feature | CLI (`attune`) | Claude Code (skills) |
| --- | --- | --- |
| Invocation | `attune workflow run` | `/security-audit` |
| Scoping | CLI flags | Socratic questions |
| Output | Terminal (Rich) | Conversation (Markdown) |
| Context-aware | No | Yes (reads your codebase) |
| CI/CD integration | Yes | No |
| Follow-up | Manual re-invocation | Interactive (e.g., "fix this?") |
| Cost tracking | Yes (attune costs) | Via MCP tools |
| Setup | `pip install` + API key | Plugin install |

## When to Use Each

**Choose the CLI** for scripting, CI/CD pipelines, and batch operations where automation and repeatability matter.

**Choose Claude Code skills** for interactive development sessions where codebase context and conversational follow-up improve results.

## Related Topics

*No related topics yet.*
