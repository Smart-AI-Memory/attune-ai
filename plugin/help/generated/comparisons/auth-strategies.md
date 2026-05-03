---
name: auth-strategies
source: src/attune/models/auth_cli.py
summary: This template explains the differences between subscription-based and API
  key authentication methods for attune-ai's connection to the Anthropic API, helping
  developers choose the authentication strategy that best fits their use case.
tags:
- auth
- setup
type: comparison
---

# Comparison: Authentication strategies

Choose how attune-ai authenticates with the Anthropic API.

| Feature | Subscription | API Key |
|---|---|---|
| Setup | Automatic (Claude Code) | Set `ANTHROPIC_API_KEY` |
| Cost | Included in subscription | Pay per token |
| Tier routing | Limited | Full (`CHEAP` / `CAPABLE` / `PREMIUM`) |
| Large files | May hit limits | Full control |
| CI/CD | Not supported | Supported |
| Best for | Quick start, small projects | Production, cost optimization |

## Recommendation

**Subscription** authentication works out of the box and requires no configuration, making it the best choice for most users getting started.

Switch to **API Key** authentication when you need any of the following:

- **CI/CD integration** — Subscription-based auth is not available in automated pipeline environments.
- **Tier routing** — Route requests across `CHEAP`, `CAPABLE`, and `PREMIUM` tiers to optimize cost and performance.
- **Large codebase support** — Avoid subscription limits when processing large files or repositories.

## Related topics

_No related topics yet._
