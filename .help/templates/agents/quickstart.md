---
type: quickstart
name: agents-quickstart
feature: agents
depth: quickstart
generated_at: 2026-06-23T22:44:18.994422+00:00
source_hash: 9f8352e822bbdc7e4000d3afae65bd38c29cb5a219fd6aded8e91de285f5a54a
status: generated
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
