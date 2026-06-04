---
type: quickstart
name: agents-quickstart
feature: agents
depth: quickstart
generated_at: 2026-06-04T23:45:26.762514+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Quickstart: Agents

Run your first agent using Attune's Universal Agent Factory.

```python
from attune.agent_factory.adapters import get_langchain_adapter

adapter = get_langchain_adapter()
agent = adapter.create_agent(config)
result = agent.invoke("Summarize the release status.")
print(result)
```

Expected output:
```
{'output': 'All checks passed. No blockers found.', 'metadata': {...}}
```

## Prerequisites

- The project is cloned and installed locally
- At least one supported framework is installed (LangChain, AutoGen, or Haystack)
- A valid `AgentConfig` object is available

## Step 1: Choose and load an adapter

Pick the framework adapter that matches your environment. Each function performs a lazy import, so only the framework you use is loaded:

| Framework | Loader function |
|---|---|
| LangChain | `get_langchain_adapter()` |
| LangGraph | `get_langgraph_adapter()` |
| AutoGen | `get_autogen_adapter()` |
| Haystack | `get_haystack_adapter()` |

```python
from attune.agent_factory.adapters import get_langchain_adapter

adapter = get_langchain_adapter()
print(adapter.framework_name)   # → 'langchain'
print(adapter.is_available())   # → True
```

## Step 2: Create an agent

Pass an `AgentConfig` to `create_agent()`. The adapter returns a `LangChainAgent` (or the equivalent for your chosen framework) that you can invoke immediately:

```python
from attune.agent_factory import AgentConfig

config = AgentConfig(name="my-agent", model_tier="capable")
agent = adapter.create_agent(config)
```

## Step 3: Invoke the agent and inspect the result

Call `invoke()` with a string or dict. Print the result to confirm the shape:

```python
result = agent.invoke("List any open blockers for the current release.")
print(result)
# {'output': '...', 'metadata': {'tokens_used': 312, ...}}
```

A dict with an `output` key confirms the agent ran successfully.

## Step 4: Wrap an existing wizard (optional shortcut)

If you already have a wizard object, use `wrap_wizard()` to convert it to an agent without writing a full `AgentConfig`:

```python
from attune.agent_factory.adapters import wrap_wizard

agent = wrap_wizard(my_wizard, name="release-checker", model_tier="capable")
result = agent.invoke("Check test coverage.")
print(result)
```

---

## Next:

Read the **Concept: Agents** page — say **"what are Attune agents?"** — to understand `AgentConfig`, `WorkflowConfig`, and how `ReleasePrepTeam` orchestrates multiple agents together.
