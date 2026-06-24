---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: task
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Tasks

### Build and run a single agent

**Goal:** create one agent and get a result.

**Steps:**

```python
import asyncio

from attune.agent_factory import AgentFactory, AgentRole


async def main() -> None:
    factory = AgentFactory()
    reviewer = factory.create_agent(
        name="reviewer",
        role=AgentRole.REVIEWER,
        model_tier="capable",
    )
    result = await reviewer.invoke({"code": "def f(): return 1/0"})
    print(result)


asyncio.run(main())
```

**Verify:** `invoke` is a coroutine — `await` it; it returns a `dict`.
`role` accepts an `AgentRole` (or its string). `model_tier` is
`"cheap"` / `"capable"` / `"premium"`.

### Orchestrate a multi-agent workflow

**Goal:** coordinate several agents and run them.

**Steps:**

```python
import asyncio

from attune.agent_factory import AgentFactory


async def main() -> None:
    factory = AgentFactory()
    researcher = factory.create_researcher()
    writer = factory.create_writer()
    workflow = factory.create_workflow(
        name="research-and-write",
        agents=[researcher, writer],
        mode="sequential",
    )
    result = await workflow.run("Summarize attune's memory tiers.")
    print(result)


asyncio.run(main())
```

**Verify:** `run` is a coroutine — `await` it; it returns a `dict`.
The role-preset shortcuts (`create_researcher`, `create_writer`, …)
return `BaseAgent`s. For ready-made pipelines, use
`create_code_review_pipeline()` or `create_research_pipeline(topic)`.

### Pick or switch the framework

**Goal:** choose a backend and see what's installed.

**Steps:**

```python
from attune.agent_factory import AgentFactory, Framework

print(AgentFactory.list_frameworks(installed_only=True))
print(AgentFactory.recommend_framework("general"))   # -> Framework.NATIVE

factory = AgentFactory(framework=Framework.LANGGRAPH)
factory.switch_framework("native")
```

**Verify:** `list_frameworks` and `recommend_framework` are callable on
the class. `Framework` values are `native`, `langchain`, `langgraph`,
`autogen`, `haystack`. Non-native frameworks are optional deps —
`list_frameworks(installed_only=True)` shows only those installed.
