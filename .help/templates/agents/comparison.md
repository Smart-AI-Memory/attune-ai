---
type: comparison
name: agents-comparison
feature: agents
depth: comparison
generated_at: 2026-06-23T22:44:18.994422+00:00
source_hash: 9f8352e822bbdc7e4000d3afae65bd38c29cb5a219fd6aded8e91de285f5a54a
status: generated
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
