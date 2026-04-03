---
type: comparison
name: auth-strategies
tags: [auth, setup]
source: src/attune/models/auth_cli.py
---

# Comparison: Authentication strategies

Choosing how attune-ai authenticates with the Anthropic API.

| Feature | Subscription | API Key |
| ------- | ------- | ------- |
| Setup | Automatic (Claude Code) | Set ANTHROPIC_API_KEY |
| Cost | Included in subscription | Pay per token |
| Tier routing | Limited | Full (CHEAP/CAPABLE/PREMIUM) |
| Large files | May hit limits | Full control |
| CI/CD | Not available | Yes |
| Best for | Quick start, small projects | Production, cost optimization |

## Recommendation

**Subscription** works out of the box for most users. Switch to **API Key** when you need CI/CD, tier routing for cost savings, or processing large codebases.

## Related Topics

_No related topics yet._
