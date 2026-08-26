"""Attune AI - Universal Agent Factory

Create agents using your preferred framework while retaining Empathy's
cost optimization, pattern learning, and memory features.

Supported Frameworks:
- LangChain: Chains, tools, and retrieval
- LangGraph: Stateful multi-agent graphs
- AutoGen: Conversational multi-agent systems
- Haystack: RAG and document pipelines
- Native: Empathy's built-in agent system

Usage:
    from attune.agent_factory import AgentFactory, Framework

    # Create factory with preferred framework
    factory = AgentFactory(framework=Framework.LANGGRAPH)

    # Create agents
    researcher = factory.create_agent("researcher", tools=[...])
    writer = factory.create_agent("writer", model_tier="premium")

    # Create workflows
    pipeline = factory.create_workflow([researcher, writer])

    # Create role-specialized agents with sensible defaults
    debugger = factory.create_debugger()

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.agent_factory.base import (
    AgentCapability,
    AgentConfig,
    AgentGraphConfig,
    AgentRole,
    BaseAdapter,
    BaseAgent,
)
from attune.agent_factory.factory import AgentFactory
from attune.agent_factory.framework import Framework

__all__ = [
    "AgentCapability",
    "AgentConfig",
    "AgentFactory",
    "AgentRole",
    "BaseAdapter",
    "BaseAgent",
    "Framework",
    "AgentGraphConfig",
    "WorkflowConfig",  # REMOVE IN v16.0.0 — deprecated alias
]


def __getattr__(name: str) -> object:
    """Serve the deprecated `WorkflowConfig` name. REMOVE IN v16.0.0."""
    if name != "WorkflowConfig":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import warnings

    warnings.warn(
        "attune.agent_factory.WorkflowConfig is deprecated and will be "
        "removed in v16.0.0. Use AgentGraphConfig instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return AgentGraphConfig
