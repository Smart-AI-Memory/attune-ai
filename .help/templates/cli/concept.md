---
type: concept
feature: cli
depth: concept
generated_at: 2026-05-04T02:33:52.698850+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI

## What

The CLI is attune's command-line interface for cost tracking, documentation browsing, and memory management. It combines direct command routing with intelligent input routing that learns from your usage patterns to suggest the most relevant Claude Code skills.

## Why

The CLI serves as both a traditional command interface and an adaptive learning system. Instead of forcing you to memorize exact command syntax, it watches how you work and builds routing preferences that improve over time. This matters when you need quick access to cost data, help documentation, or stored lessons without breaking your development flow.

## Core responsibilities

The CLI handles three primary workflows:

**Cost tracking** — Monitor spending with `attune costs`, view daily summaries with `attune costs today`, export data for analysis, and reset tracking when needed.

**Help browsing** — Access structured documentation templates through `attune help`, letting you explore concepts, tasks, references, and troubleshooting guides without leaving the terminal.

**Memory management** — Store and retrieve lessons with `attune remember` and `attune lessons`, plus manage cross-session memory for persistent context between Claude conversations.

## Intelligent routing

The `HybridRouter` component learns your preferences as you work. When you type `attune help migration`, it remembers that you often want the task template rather than the concept. The `RoutingPreference` class tracks these patterns:

- **keyword** — The term you searched for
- **skill** — Which Claude Code skill you actually chose
- **usage_count** — How often this preference applies
- **confidence** — How certain the system is about this routing

This creates a personalized command experience that adapts to your specific workflow patterns.

## Implementation structure

The CLI spans 10 source files, organizing functionality into focused command modules. Cost commands handle financial tracking, help commands bridge to the documentation system, and memory commands manage both quick lessons and persistent context storage. The routing layer sits above these modules, learning which commands you reach for most often given specific input patterns.
