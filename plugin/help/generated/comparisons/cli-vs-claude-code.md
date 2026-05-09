---
type: comparison
name: cli-vs-claude-code
tags: [cli, claude-code]
source: smartaimemory.com/attune-plugin/
---

# Comparison: CLI vs Claude Code usage

Two ways to use attune-ai: the standalone CLI or inside Claude Code conversations.

| Feature | CLI (attune) | Claude Code (skills) |
| ------- | ------- | ------- |
| Invocation | `attune workflow run` | `/security-audit` |
| Scoping | CLI flags | Socratic questions |
| Output | Terminal (Rich) | Conversation (Markdown) |
| Context-aware | No | Yes (sees your codebase) |
| CI/CD | Yes | No |
| Follow-up | Manual | Interactive ("fix this?") |
| Cost tracking | Yes (attune costs) | Via MCP tools |
| Setup | pip install + API key | Plugin install |

## Recommendation

Use the **CLI** for scripting, CI/CD, and batch operations. Use **Claude Code skills** for interactive development where context and follow-up matter.

## Related Topics

_No related topics yet._
