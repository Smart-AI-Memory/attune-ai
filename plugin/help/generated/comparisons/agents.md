---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: comparison
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Comparison

The Agent Factory is the **build-your-own-agent** surface, distinct
from the packaged workflows and from wizards:

| | agents (Factory) | workflows | wizards |
|--|------------------|-----------|---------|
| What | Create/run/orchestrate custom agents across frameworks | Pre-built analysis pipelines (security, review, …) | Interactive multi-step guided flows |
| Entry | `AgentFactory(...)` + `await invoke/run` | `attune workflow run <slug>` | `/wizard` skill + `await run()` |
| Frameworks | native / langchain / langgraph / autogen / haystack | n/a | n/a |

Reach for the **Factory** when you need bespoke agents or want
framework portability; reach for **workflows** when a packaged pipeline
already does the job; reach for **wizards** for an interactive,
user-in-the-loop task.
