"""Tests for empathy_llm_toolkit agent factory and routing modules.

Comprehensive test coverage for native adapter, factory, and model router.

Created: 2026-01-20
Coverage target: 80%+
"""

import pytest

from attune.agent_factory.adapters.native import (
    NativeAdapter,
    NativeAgent,
    NativeWorkflow,
)
from attune.agent_factory.base import (
    AgentCapability,
    AgentConfig,
    AgentGraphConfig,
    AgentRole,
)
from attune.agent_factory.factory import AgentFactory
from attune.agent_factory.framework import Framework
from attune.routing.model_router import (
    ModelConfig,
    ModelRouter,
    ModelTier,
    TaskRouting,
)

# =============================================================================
# Native Adapter Tests
# =============================================================================


class TestNativeAgent:
    """Tests for NativeAgent."""

    def test_init(self):
        """Test agent initialization."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = NativeAgent(config)

        assert agent.name == "test_agent"
        assert agent.role == AgentRole.RESEARCHER
        assert agent._llm is None
        assert agent._tools == {}

    def test_init_with_tools(self):
        """Test agent initialization with tools."""
        tools = [
            {"name": "tool1", "func": lambda x: x},
            {"name": "tool2", "func": lambda x: x * 2},
        ]
        config = AgentConfig(name="tool_agent", tools=tools)
        agent = NativeAgent(config)

        assert "tool1" in agent._tools
        assert "tool2" in agent._tools

    @pytest.mark.asyncio
    async def test_invoke_string_input(self):
        """Test invoking agent with string input."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke("Hello, help me")

        assert "output" in result
        assert "metadata" in result
        assert "model" in result["metadata"]
        # Without LLM, should use fallback response
        assert "[test_agent]" in result["output"]

    @pytest.mark.asyncio
    async def test_invoke_dict_input(self):
        """Test invoking agent with dict input."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke({"input": "Process this"})

        assert "Process this" in result["output"]

    @pytest.mark.asyncio
    async def test_invoke_dict_input_query_key(self):
        """Test invoking agent with dict input using 'query' key."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke({"query": "Query this"})

        assert "Query this" in result["output"]

    @pytest.mark.asyncio
    async def test_invoke_empty_input(self):
        """Test invoking agent with empty input."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke("")

        assert result["output"] == ""
        assert result["metadata"]["skipped"] is True

    @pytest.mark.asyncio
    async def test_invoke_whitespace_input(self):
        """Test invoking agent with whitespace input."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke("   ")

        assert result["output"] == ""
        assert result["metadata"]["skipped"] is True

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invoking agent with context."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        result = await agent.invoke("Test", context={"extra": "data"})

        assert "output" in result

    @pytest.mark.asyncio
    async def test_invoke_updates_history(self):
        """Test that invoke updates conversation history."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        await agent.invoke("First message")
        await agent.invoke("Second message")

        history = agent.get_conversation_history()
        assert len(history) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_stream(self):
        """Test streaming agent response."""
        config = AgentConfig(name="test_agent")
        agent = NativeAgent(config)

        results = []
        async for chunk in agent.stream("Test input"):
            results.append(chunk)

        # Native adapter yields single full response
        assert len(results) == 1
        assert "output" in results[0]


class TestNativeWorkflow:
    """Tests for NativeWorkflow."""

    @pytest.fixture
    def agents(self):
        """Create test agents."""
        config1 = AgentConfig(name="agent1", role=AgentRole.RESEARCHER)
        config2 = AgentConfig(name="agent2", role=AgentRole.WRITER)
        return [NativeAgent(config1), NativeAgent(config2)]

    @pytest.mark.asyncio
    async def test_run_sequential(self, agents):
        """Test running workflow sequentially."""
        config = AgentGraphConfig(name="test_workflow", mode="sequential")
        workflow = NativeWorkflow(config, agents)

        result = await workflow.run("Test input")

        assert "output" in result
        assert "results" in result
        assert len(result["results"]) == 2
        assert result["agents_invoked"] == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_run_parallel(self, agents):
        """Test running workflow in parallel."""
        config = AgentGraphConfig(name="test_workflow", mode="parallel")
        workflow = NativeWorkflow(config, agents)

        result = await workflow.run("Test input")

        assert "output" in result
        assert "results" in result
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_run_with_initial_state(self, agents):
        """Test running workflow with initial state."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = NativeWorkflow(config, agents)

        result = await workflow.run("Test", initial_state={"key": "value"})

        assert result["state"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_run_unknown_mode_defaults_to_sequential(self, agents):
        """Test that unknown mode defaults to sequential."""
        config = AgentGraphConfig(name="test_workflow", mode="unknown_mode")
        workflow = NativeWorkflow(config, agents)

        result = await workflow.run("Test")

        # Should work (defaults to sequential)
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_stream(self, agents):
        """Test streaming workflow."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = NativeWorkflow(config, agents)

        events = []
        async for event in workflow.stream("Test input"):
            events.append(event)

        # Should have start, output, end for each agent
        assert any(e["event"] == "agent_start" for e in events)
        assert any(e["event"] == "agent_output" for e in events)
        assert any(e["event"] == "agent_end" for e in events)


class TestNativeAdapter:
    """Tests for NativeAdapter."""

    def test_init_default(self):
        """Test default initialization."""
        adapter = NativeAdapter()

        assert adapter.provider == "anthropic"
        assert adapter.framework_name == "native"

    def test_init_custom_provider(self):
        """Test initialization with custom provider."""
        adapter = NativeAdapter(provider="openai", api_key="test_key")

        assert adapter.provider == "openai"
        assert adapter.api_key == "test_key"

    def test_is_available(self):
        """Test that native adapter is always available."""
        adapter = NativeAdapter()
        assert adapter.is_available() is True

    def test_create_agent(self):
        """Test creating an agent."""
        adapter = NativeAdapter()
        config = AgentConfig(name="test_agent", role=AgentRole.WRITER)

        agent = adapter.create_agent(config)

        assert isinstance(agent, NativeAgent)
        assert agent.name == "test_agent"

    def test_create_workflow(self):
        """Test creating a workflow."""
        adapter = NativeAdapter()
        config = AgentGraphConfig(name="test_workflow")
        agents = [
            NativeAgent(AgentConfig(name="agent1")),
            NativeAgent(AgentConfig(name="agent2")),
        ]

        workflow = adapter.create_workflow(config, agents)

        assert isinstance(workflow, NativeWorkflow)
        assert "agent1" in workflow.agents
        assert "agent2" in workflow.agents

    def test_create_tool(self):
        """Test creating a tool."""
        adapter = NativeAdapter()

        tool = adapter.create_tool(
            name="test_tool",
            description="A test tool",
            func=lambda x: x * 2,
            args_schema={"x": "int"},
        )

        assert tool["name"] == "test_tool"
        assert tool["description"] == "A test tool"
        assert tool["func"](5) == 10
        assert tool["args_schema"] == {"x": "int"}


# =============================================================================
# Agent Factory Tests
# =============================================================================


class TestAgentFactory:
    """Tests for AgentFactory."""

    def test_init_default(self):
        """Test default initialization."""
        factory = AgentFactory()

        assert factory.provider == "anthropic"
        assert factory.framework in [Framework.NATIVE, Framework.LANGGRAPH, Framework.LANGCHAIN]

    def test_init_with_framework_string(self):
        """Test initialization with framework string."""
        factory = AgentFactory(framework="native")

        assert factory.framework == Framework.NATIVE

    def test_init_with_framework_enum(self):
        """Test initialization with framework enum."""
        factory = AgentFactory(framework=Framework.NATIVE)

        assert factory.framework == Framework.NATIVE

    def test_adapter_property(self):
        """Test adapter property."""
        factory = AgentFactory(framework=Framework.NATIVE)

        assert factory.adapter is not None
        assert factory.adapter.framework_name == "native"

    def test_create_agent_basic(self):
        """Test basic agent creation."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_agent(name="test_agent")

        assert agent.name == "test_agent"
        assert "test_agent" in factory._agents

    def test_create_agent_with_role_string(self):
        """Test agent creation with role as string."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_agent(name="researcher", role="researcher")

        assert agent.role == AgentRole.RESEARCHER

    def test_create_agent_with_invalid_role_string(self):
        """Test agent creation with invalid role string."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_agent(name="test", role="invalid_role")

        # Should fallback to CUSTOM
        assert agent.role == AgentRole.CUSTOM

    def test_create_agent_with_capabilities(self):
        """Test agent creation with capabilities."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_agent(
            name="capable_agent",
            capabilities=[AgentCapability.CODE_EXECUTION, AgentCapability.WEB_SEARCH],
        )

        assert AgentCapability.CODE_EXECUTION in agent.config.capabilities

    def test_create_workflow(self):
        """Test workflow creation."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent1 = factory.create_agent(name="agent1")
        agent2 = factory.create_agent(name="agent2")

        workflow = factory.create_workflow(
            name="test_workflow",
            agents=[agent1, agent2],
            mode="sequential",
        )

        assert workflow.config.name == "test_workflow"
        assert len(workflow.agents) == 2

    def test_create_tool(self):
        """Test tool creation."""
        factory = AgentFactory(framework=Framework.NATIVE)

        tool = factory.create_tool(
            name="calculator",
            description="Calculates things",
            func=lambda x, y: x + y,
        )

        assert tool["name"] == "calculator"

    def test_get_agent(self):
        """Test getting created agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        factory.create_agent(name="my_agent")
        found = factory.get_agent("my_agent")

        assert found is not None
        assert found.name == "my_agent"

    def test_get_agent_not_found(self):
        """Test getting non-existent agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        found = factory.get_agent("nonexistent")

        assert found is None

    def test_list_agents(self):
        """Test listing created agents."""
        factory = AgentFactory(framework=Framework.NATIVE)

        factory.create_agent(name="agent1")
        factory.create_agent(name="agent2")

        agents = factory.list_agents()

        assert "agent1" in agents
        assert "agent2" in agents

    def test_list_frameworks_installed_only(self):
        """Test listing installed frameworks."""
        frameworks = AgentFactory.list_frameworks(installed_only=True)

        assert len(frameworks) >= 1
        # Native should always be available
        native_found = any(f["framework"] == Framework.NATIVE for f in frameworks)
        assert native_found

    def test_list_frameworks_all(self):
        """Test listing all frameworks."""
        frameworks = AgentFactory.list_frameworks(installed_only=False)

        assert len(frameworks) >= 5  # NATIVE, LANGCHAIN, LANGGRAPH, AUTOGEN, HAYSTACK

    def test_recommend_framework(self):
        """Test framework recommendation."""
        recommended = AgentFactory.recommend_framework("general")

        assert recommended in Framework

    def test_switch_framework(self):
        """Test switching frameworks."""
        factory = AgentFactory(framework=Framework.NATIVE)
        factory.create_agent(name="old_agent")

        factory.switch_framework("native")  # Switch to same framework (still valid)

        # Agents should be cleared
        assert len(factory._agents) == 0

    # Convenience method tests

    def test_create_researcher(self):
        """Test creating researcher agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_researcher()

        assert agent.role == AgentRole.RESEARCHER
        assert agent.name == "researcher"

    def test_create_writer(self):
        """Test creating writer agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_writer()

        assert agent.role == AgentRole.WRITER

    def test_create_reviewer(self):
        """Test creating reviewer agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_reviewer()

        assert agent.role == AgentRole.REVIEWER

    def test_create_debugger(self):
        """Test creating debugger agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_debugger()

        assert agent.role == AgentRole.DEBUGGER
        assert AgentCapability.CODE_EXECUTION in agent.config.capabilities

    def test_create_coordinator(self):
        """Test creating coordinator agent."""
        factory = AgentFactory(framework=Framework.NATIVE)

        agent = factory.create_coordinator()

        assert agent.role == AgentRole.COORDINATOR

    def test_create_research_pipeline(self):
        """Test creating research pipeline."""
        factory = AgentFactory(framework=Framework.NATIVE)

        pipeline = factory.create_research_pipeline(topic="AI trends")

        assert pipeline.config.name == "research_pipeline"
        assert len(pipeline.agents) == 3  # researcher, writer, reviewer

    def test_create_research_pipeline_no_reviewer(self):
        """Test creating research pipeline without reviewer."""
        factory = AgentFactory(framework=Framework.NATIVE)

        pipeline = factory.create_research_pipeline(include_reviewer=False)

        assert len(pipeline.agents) == 2  # researcher, writer only

    def test_create_code_review_pipeline(self):
        """Test creating code review pipeline."""
        factory = AgentFactory(framework=Framework.NATIVE)

        pipeline = factory.create_code_review_pipeline()

        assert pipeline.config.name == "code_review_pipeline"
        assert len(pipeline.agents) == 3  # analyzer, debugger, reviewer


# =============================================================================
# Model Router Tests
# =============================================================================


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_values(self):
        """Test tier values."""
        assert ModelTier.CHEAP.value == "cheap"
        assert ModelTier.CAPABLE.value == "capable"
        assert ModelTier.PREMIUM.value == "premium"


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_creation(self):
        """Test creating model config."""
        config = ModelConfig(
            model_id="test-model",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
            max_tokens=4096,
            supports_tools=True,
        )

        assert config.model_id == "test-model"
        assert config.cost_per_1k_input == 0.001
        assert config.cost_per_1k_output == 0.002
        assert config.max_tokens == 4096
        assert config.supports_tools is True

    def test_default_values(self):
        """Test default values."""
        config = ModelConfig(
            model_id="test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        assert config.max_tokens == 4096
        assert config.supports_tools is True


class TestTaskRouting:
    """Tests for TaskRouting."""

    def test_get_tier_cheap(self):
        """Test getting cheap tier for appropriate tasks."""
        # Cheap tasks
        tier = TaskRouting.get_tier("summarize")
        assert tier == ModelTier.CHEAP

    def test_get_tier_capable(self):
        """Test getting capable tier for appropriate tasks."""
        # Capable tasks
        tier = TaskRouting.get_tier("generate_code")
        assert tier == ModelTier.CAPABLE

    def test_get_tier_premium(self):
        """Test getting premium tier for appropriate tasks."""
        # Premium tasks
        tier = TaskRouting.get_tier("coordinate")
        assert tier == ModelTier.PREMIUM


class TestModelRouter:
    """Tests for ModelRouter."""

    def test_init_default(self):
        """Test default initialization."""
        router = ModelRouter()

        assert router._default_provider == "anthropic"
        assert router._custom_routing == {}

    def test_init_custom_provider(self):
        """Test initialization with custom provider."""
        router = ModelRouter(default_provider="openai")

        assert router._default_provider == "openai"

    def test_init_custom_routing(self):
        """Test initialization with custom routing."""
        custom = {"my_task": ModelTier.PREMIUM}
        router = ModelRouter(custom_routing=custom)

        assert router._custom_routing == custom

    def test_route_basic(self):
        """Test basic routing."""
        router = ModelRouter()

        model = router.route("summarize")

        assert isinstance(model, str)
        assert len(model) > 0

    def test_route_different_tiers(self):
        """Test routing to different tiers."""
        router = ModelRouter()

        cheap_model = router.route("summarize")
        capable_model = router.route("generate_code")
        premium_model = router.route("coordinate")

        # Models should be different (or at least strings)
        assert isinstance(cheap_model, str)
        assert isinstance(capable_model, str)
        assert isinstance(premium_model, str)

    def test_route_invalid_provider(self):
        """Test routing with invalid provider."""
        router = ModelRouter()

        with pytest.raises(ValueError, match="Unknown provider"):
            router.route("summarize", provider="invalid_provider")

    def test_get_config(self):
        """Test getting model config."""
        router = ModelRouter()

        config = router.get_config("generate_code")

        assert isinstance(config, ModelConfig)
        assert config.model_id is not None

    def test_estimate_cost(self):
        """Test cost estimation."""
        router = ModelRouter()

        cost = router.estimate_cost("summarize", input_tokens=1000, output_tokens=500)

        assert isinstance(cost, float)
        assert cost >= 0

    def test_compare_costs(self):
        """Test cost comparison across tiers."""
        router = ModelRouter()

        costs = router.compare_costs("test_task", input_tokens=1000, output_tokens=500)

        assert "cheap" in costs
        assert "capable" in costs
        assert "premium" in costs
        # Premium should be most expensive
        assert costs["premium"] >= costs["capable"]
        assert costs["capable"] >= costs["cheap"]

    def test_add_task_routing(self):
        """Test adding custom task routing."""
        router = ModelRouter()

        router.add_task_routing("my_custom_task", ModelTier.PREMIUM)

        # Should now route to premium
        tier = router.get_tier("my_custom_task")
        assert tier == ModelTier.PREMIUM

    def test_get_tier(self):
        """Test getting tier for task."""
        router = ModelRouter()

        tier = router.get_tier("summarize")

        assert tier == ModelTier.CHEAP

    def test_get_tier_with_custom_routing(self):
        """Test getting tier with custom routing."""
        router = ModelRouter(custom_routing={"custom_task": ModelTier.CHEAP})

        tier = router.get_tier("custom_task")

        assert tier == ModelTier.CHEAP

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = ModelRouter.get_supported_providers()

        assert "anthropic" in providers
        assert len(providers) == 1  # Anthropic-only architecture

    def test_get_all_tasks(self):
        """Test getting all tasks by tier."""
        tasks = ModelRouter.get_all_tasks()

        assert "cheap" in tasks
        assert "capable" in tasks
        assert "premium" in tasks
        assert len(tasks["cheap"]) > 0
        assert len(tasks["capable"]) > 0
        assert len(tasks["premium"]) > 0

    def test_calculate_savings(self):
        """Test savings calculation."""
        router = ModelRouter()

        savings = router.calculate_savings("summarize", input_tokens=1000, output_tokens=500)

        assert "task_type" in savings
        assert "routed_tier" in savings
        assert "routed_cost" in savings
        assert "premium_cost" in savings
        assert "savings" in savings
        assert "savings_percent" in savings

        # Routing to cheap should save money vs premium
        assert savings["savings"] >= 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestAgentFactoryIntegration:
    """Integration tests for agent factory."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(
        reason="Integration test requiring valid ANTHROPIC_API_KEY - run manually with: pytest -m integration",
    )
    async def test_full_workflow_execution(self):
        """Test complete workflow from factory creation to execution."""
        factory = AgentFactory(framework=Framework.NATIVE)

        # Create agents
        researcher = factory.create_researcher()
        writer = factory.create_writer()

        # Create workflow
        workflow = factory.create_workflow(
            name="test_pipeline",
            agents=[researcher, writer],
            mode="sequential",
        )

        # Execute
        result = await workflow.run("Research and write about Python testing")

        assert "output" in result
        assert len(result["results"]) == 2
        assert result["agents_invoked"] == ["researcher", "writer"]
