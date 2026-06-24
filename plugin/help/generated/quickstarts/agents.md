---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: quickstart
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Quickstart

Create an agent and invoke it. `invoke` is a coroutine, so drive it
with `asyncio.run`:

```python
import asyncio

from attune.agent_factory import AgentFactory


async def main() -> None:
    factory = AgentFactory()  # native framework by default
    agent = factory.create_agent(
        name="helper",
        description="Answers questions about the codebase.",
    )
    result = await agent.invoke("What does the release-prep gate check?")
    print(result)


asyncio.run(main())
```

`AgentFactory()` uses the `native` framework; pass
`AgentFactory(framework="langgraph")` (or a `Framework` value) to use
another backend.
