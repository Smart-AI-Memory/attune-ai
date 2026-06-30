# Agent Factory

Create agents using your preferred framework while retaining
Attune's cost optimization, pattern learning, and memory
features.

## Quick Start

```python
from attune.agent_factory import AgentFactory, Framework

# Auto-detect best framework (or specify one)
factory = AgentFactory(framework=Framework.LANGGRAPH)

# Create agents
researcher = factory.create_researcher(model_tier="capable")
writer = factory.create_writer(model_tier="premium")

# Run
result = await researcher.invoke("Research AI trends in 2026")
```

## Installation

The native adapter works with zero extra dependencies:

```bash
pip install 'attune-ai'
```

For other frameworks, install the corresponding package:

```bash
pip install langchain langchain-anthropic   # LangChain
pip install langgraph langchain-anthropic    # LangGraph
pip install pyautogen                        # AutoGen
pip install haystack-ai                      # Haystack
```

## Frameworks

| Framework | Best For | Auto-Detected |
|-----------|----------|---------------|
| Native | Simple agents, cost optimization | Always |
| LangChain | Chains, tools, RAG | Yes |
| LangGraph | Stateful multi-agent workflows | Yes |
| AutoGen | Conversational agent teams | Yes |
| Haystack | Document QA, NLP pipelines | Yes |

```python
# See what's available
for fw in AgentFactory.list_frameworks():
    print(f"{fw['name']}: {fw['description']}")

# Get a recommendation
best = AgentFactory.recommend_framework("rag")
```

## Creating Agents

### Basic

```python
from attune.agent_factory import AgentFactory, AgentRole

factory = AgentFactory()
agent = factory.create_agent(
    name="analyst",
    role=AgentRole.RESEARCHER,
    model_tier="capable",
    system_prompt="You analyze data thoroughly.",
)
result = await agent.invoke("Analyze Q1 sales data")
```

### With Tools

```python
search_tool = factory.create_tool(
    name="search",
    description="Search the web",
    func=my_search_function,
)
agent = factory.create_agent(
    name="web_researcher",
    role="researcher",
    tools=[search_tool],
)
```

### Convenience Factories

```python
researcher = factory.create_researcher()
writer = factory.create_writer()
reviewer = factory.create_reviewer()
debugger = factory.create_debugger()
coordinator = factory.create_coordinator()
```

## Workflows

Chain agents into pipelines:

```python
researcher = factory.create_researcher()
writer = factory.create_writer()
reviewer = factory.create_reviewer()

pipeline = factory.create_workflow(
    name="content_pipeline",
    agents=[researcher, writer, reviewer],
    mode="sequential",
)
result = await pipeline.run("Write about quantum computing")
```

### Pre-Built Pipelines

```python
# Research -> Write -> Review
pipeline = factory.create_research_pipeline(
    topic="AI safety",
    include_reviewer=True,
)

# Security -> Debug -> Review
pipeline = factory.create_code_review_pipeline()
```

### Execution Modes

| Mode | Description |
|------|-------------|
| `sequential` | Agents run one after another |
| `parallel` | Agents run concurrently |
| `graph` | Stateful graph execution |
| `conversation` | Agent-to-agent dialogue |

## Resilience

Add circuit breaker, retry, and timeout to any agent:

```python
agent = factory.create_agent(
    name="robust_agent",
    role="researcher",
    resilience_enabled=True,
    circuit_breaker_threshold=3,
    retry_max_attempts=2,
    timeout_seconds=30.0,
)
```

Or configure directly:

```python
from attune.agent_factory.resilient import (
    ResilientAgent,
    ResilienceConfig,
)

config = ResilienceConfig(
    enable_circuit_breaker=True,
    failure_threshold=5,
    enable_retry=True,
    max_attempts=3,
    enable_fallback=True,
    fallback_value={"output": "Service unavailable"},
)
agent = ResilientAgent(base_agent, config)
```

## Memory Graph

Enable cross-agent learning so agents share findings:

```python
agent = factory.create_agent(
    name="bug_hunter",
    role="debugger",
    memory_graph_enabled=True,
    store_findings=True,
    query_similar=True,
)

# Agent automatically:
# 1. Queries past findings before each invocation
# 2. Stores new findings after each invocation
```

Check graph statistics:

```python
stats = agent.get_graph_stats()
# {"enabled": True, "node_count": 42, "edge_count": 15, ...}
```

## Switching Frameworks

Switch at runtime without changing agent code:

```python
factory = AgentFactory(framework="langchain")
agent = factory.create_researcher()

# Later, switch to LangGraph
factory.switch_framework("langgraph")
agent = factory.create_researcher()  # Same API
```

## Model Tiers

The factory uses Attune's `ModelRouter` to resolve tiers to
specific model IDs:

| Tier | Use Case | Default (Anthropic) |
|------|----------|---------------------|
| `cheap` | Summarization, simple tasks | Claude Haiku |
| `capable` | Code generation, analysis | Claude Sonnet |
| `premium` | Architecture, critical decisions | Claude Opus |

Override with a specific model:

```python
agent = factory.create_agent(
    name="specific",
    model_override="claude-sonnet-5",
)
```

## Further Reading

- [API Reference](agent-factory-api.md)
- [Module Overview](agent-factory-overview.md)
