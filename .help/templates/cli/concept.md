---
type: concept
feature: cli
depth: concept
generated_at: 2026-04-23T03:31:47.611928+00:00
source_hash: 95afb1e38daa117bab7e14bf58b614da535d484b24b1dd072c4750e232202196
status: generated
---

# CLI

Attune's command-line interface provides both traditional command parsing and intelligent routing that learns from your usage patterns.

## Core architecture

The CLI operates as a hybrid system that handles two types of input:

- **Slash commands** — Traditional CLI commands like `/costs today` or `/help memory`
- **Natural language** — Plain text that gets routed to appropriate skills based on learned preferences

At the center is the **HybridRouter**, which maintains a preference database of how you typically want certain keywords handled. When you type "show costs," it remembers that you usually want the cost summary skill rather than a general search.

## Intelligent routing

The router builds preferences automatically through usage tracking:

- **RoutingPreference** stores each learned association between a keyword, skill, and arguments
- **Confidence scoring** increases when you repeatedly choose the same routing for a keyword
- **Usage counting** tracks how often each preference gets applied

For example, after you run "show costs" a few times and select the cost tracking skill, the router learns to suggest that skill first for similar input.

## Command categories

The CLI organizes functionality into focused command groups:

| Category | Purpose | Example commands |
|----------|---------|------------------|
| **Cost tracking** | Monitor and export API usage costs | `costs today`, `costs export` |
| **Help browsing** | Navigate documentation templates | `help memory`, `help search` |
| **Memory management** | Store and recall context | `remember`, `forget topic` |

## Command discovery

Unlike traditional CLIs that require memorizing syntax, Attune's interface adapts to how you naturally express intent. The router provides suggestions based on partial input and learns which commands you actually use, making the most relevant options easier to access over time.
