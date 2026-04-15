---
type: concept
feature: cli
depth: concept
generated_at: 2026-04-14T15:10:37.765524+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI

The Attune CLI is a hybrid command-line interface that routes user input between traditional commands and natural language processing through Claude Code skills.

## Core architecture

The CLI operates on two levels: structured commands for specific operations and intelligent routing for natural language queries.

**Traditional commands** handle concrete tasks like cost tracking (`attune costs today`) and help browsing (`attune help`). These commands follow standard CLI patterns with defined arguments and predictable outputs.

**Intelligent routing** processes natural language input through the `HybridRouter`, which learns from user patterns and maps queries to appropriate Claude Code skill invocations. When you type something like "analyze my recent costs," the router determines whether to use a built-in command or delegate to a skill.

## Key components

**`HybridRouter`** serves as the decision engine, maintaining learned preferences about how keywords map to skills. It tracks usage patterns and confidence levels to improve routing accuracy over time.

**`RoutingPreference`** captures these learned associations, storing the keyword that triggered a skill, the skill name, any arguments used, and confidence metrics based on usage frequency.

**Command modules** implement specific CLI operations:
- Cost tracking commands export usage data, show daily summaries, and reset tracking history
- Help commands browse documentation templates across categories like errors, warnings, and tips
- Learning commands manage the router's preference system

## Routing intelligence

The router maintains user-specific preferences in a local file, learning which skills you prefer for different types of input. When you use a slash command format (like `/analyze costs`), it bypasses the intelligence layer and directly invokes the specified skill.

For ambiguous input, the router provides suggestions based on partial matches against learned preferences, helping you discover relevant skills without memorizing exact command syntax.
