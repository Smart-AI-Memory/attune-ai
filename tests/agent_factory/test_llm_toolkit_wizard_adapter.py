"""Tests for empathy_llm_toolkit wizard_adapter module.

Comprehensive test coverage for WizardAgent, WizardWorkflow, and WizardAdapter.

Created: 2026-01-20
Coverage target: 80%+
"""

import pytest

from attune.agent_factory.adapters.wizard_adapter import (
    WizardAdapter,
    WizardAgent,
    WizardWorkflow,
    wrap_wizard,
)
from attune.agent_factory.base import AgentConfig, AgentGraphConfig, AgentRole

# =============================================================================
# Mock Wizard Classes
# =============================================================================


class MockWizard:
    """Mock wizard for testing."""

    name = "MockWizard"
    level = 4

    async def analyze(self, context: dict) -> dict:
        return {
            "output": f"Analyzed: {context.get('input', '')}",
            "confidence": 0.85,
            "predictions": ["pred1", "pred2"],
            "recommendations": ["rec1", "rec2"],
            "patterns": [],
        }


class MockWizardWithoutName:
    """Mock wizard without name attribute."""

    level = 3

    async def analyze(self, context: dict) -> dict:
        return {"output": "result", "confidence": 0.5}


class MockWizardCustomResponse:
    """Mock wizard returning different response formats."""

    name = "CustomResponseWizard"

    def __init__(self, response_format="output"):
        self.response_format = response_format

    async def analyze(self, context: dict) -> dict:
        if self.response_format == "response":
            return {"response": "response value"}
        if self.response_format == "result":
            return {"result": ["item1", "item2"]}
        if self.response_format == "analysis":
            return {"analysis": {"key": "value"}}
        if self.response_format == "recommendations_only":
            return {"recommendations": ["rec1", "rec2"]}
        if self.response_format == "empty":
            return {}
        return {"output": "default"}


# =============================================================================
# WizardAgent Tests
# =============================================================================


class TestWizardAgent:
    """Tests for WizardAgent class."""

    def test_init(self):
        """Test WizardAgent initialization."""
        wizard = MockWizard()
        config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            model_tier="capable",
        )

        agent = WizardAgent(wizard, config)

        assert agent._wizard is wizard
        assert agent._wizard_name == "MockWizard"
        assert agent._wizard_level == 4

    def test_init_wizard_without_name(self):
        """Test initialization with wizard without name attribute."""
        wizard = MockWizardWithoutName()
        config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            model_tier="capable",
        )

        agent = WizardAgent(wizard, config)

        assert agent._wizard_name == "MockWizardWithoutName"
        assert agent._wizard_level == 3

    def test_wizard_property(self):
        """Test wizard property."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.CUSTOM)
        agent = WizardAgent(wizard, config)

        assert agent.wizard is wizard

    def test_wizard_level_property(self):
        """Test wizard_level property."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.CUSTOM)
        agent = WizardAgent(wizard, config)

        assert agent.wizard_level == 4

    @pytest.mark.asyncio
    async def test_invoke_with_string_input(self):
        """Test invoke with string input."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test input")

        assert "output" in result
        assert "Analyzed: test input" in result["output"]
        assert result["metadata"]["wizard"] == "MockWizard"
        assert result["metadata"]["level"] == 4
        assert result["predictions"] == ["pred1", "pred2"]

    @pytest.mark.asyncio
    async def test_invoke_with_dict_input(self):
        """Test invoke with dict input."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke({"input": "dict input", "extra": "data"})

        assert "output" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invoke with additional context."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        context = {"session_id": "123", "user": "test_user"}
        result = await agent.invoke("test", context=context)

        assert "output" in result

    @pytest.mark.asyncio
    async def test_invoke_tracks_conversation_history(self):
        """Test that invoke tracks conversation history."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        await agent.invoke("first message")
        await agent.invoke("second message")

        assert len(agent._conversation_history) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_stream(self):
        """Test stream method."""
        wizard = MockWizard()
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        results = []
        async for result in agent.stream("test input"):
            results.append(result)

        assert len(results) == 1
        assert "output" in results[0]


class TestExtractOutput:
    """Tests for _extract_output method."""

    @pytest.mark.asyncio
    async def test_extract_output_from_output_key(self):
        """Test extracting output from 'output' key."""
        wizard = MockWizardCustomResponse("output")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        assert result["output"] == "default"

    @pytest.mark.asyncio
    async def test_extract_output_from_response_key(self):
        """Test extracting output from 'response' key."""
        wizard = MockWizardCustomResponse("response")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        assert result["output"] == "response value"

    @pytest.mark.asyncio
    async def test_extract_output_from_result_list(self):
        """Test extracting output from list result."""
        wizard = MockWizardCustomResponse("result")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        assert "item1" in result["output"]
        assert "item2" in result["output"]

    @pytest.mark.asyncio
    async def test_extract_output_from_analysis_dict(self):
        """Test extracting output from dict analysis."""
        wizard = MockWizardCustomResponse("analysis")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        assert "key" in result["output"]

    @pytest.mark.asyncio
    async def test_extract_output_from_recommendations(self):
        """Test extracting output from recommendations."""
        wizard = MockWizardCustomResponse("recommendations_only")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        assert "rec1" in result["output"]
        assert "rec2" in result["output"]

    @pytest.mark.asyncio
    async def test_extract_output_fallback_stringify(self):
        """Test extracting output with fallback to stringify."""
        wizard = MockWizardCustomResponse("empty")
        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, config)

        result = await agent.invoke("test")
        # Should stringify the empty dict
        assert isinstance(result["output"], str)


# =============================================================================
# WizardWorkflow Tests
# =============================================================================


class TestWizardWorkflow:
    """Tests for WizardWorkflow class."""

    @pytest.mark.asyncio
    async def test_run_empty_workflow(self):
        """Test running workflow with no agents."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = WizardWorkflow(config, [])

        result = await workflow.run("test input")

        assert result["output"] == ""
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_run_single_agent_workflow(self):
        """Test running workflow with single agent."""
        wizard = MockWizard()
        agent_config = AgentConfig(name="wizard1", role=AgentRole.RESEARCHER)
        agent = WizardAgent(wizard, agent_config)

        workflow_config = AgentGraphConfig(name="single_wizard")
        workflow = WizardWorkflow(workflow_config, [agent])

        result = await workflow.run("test input")

        assert len(result["results"]) == 1
        assert result["agents_invoked"] == ["wizard1"]

    @pytest.mark.asyncio
    async def test_run_multi_agent_workflow(self):
        """Test running workflow with multiple agents."""
        wizard1 = MockWizard()
        wizard2 = MockWizard()
        wizard2.name = "SecondWizard"

        agent1 = WizardAgent(wizard1, AgentConfig(name="wizard1", role=AgentRole.RESEARCHER))
        agent2 = WizardAgent(wizard2, AgentConfig(name="wizard2", role=AgentRole.SUMMARIZER))

        workflow_config = AgentGraphConfig(name="multi_wizard")
        workflow = WizardWorkflow(workflow_config, [agent1, agent2])

        result = await workflow.run("test input")

        assert len(result["results"]) == 2
        assert result["agents_invoked"] == ["wizard1", "wizard2"]
        assert len(result["all_predictions"]) >= 2  # Both wizards add predictions

    @pytest.mark.asyncio
    async def test_run_with_initial_state(self):
        """Test running workflow with initial state."""
        wizard = MockWizard()
        agent = WizardAgent(wizard, AgentConfig(name="wizard", role=AgentRole.RESEARCHER))

        workflow_config = AgentGraphConfig(name="stateful_workflow")
        workflow = WizardWorkflow(workflow_config, [agent])

        initial_state = {"session_id": "123", "user": "test"}
        result = await workflow.run("test", initial_state=initial_state)

        assert result["state"]["session_id"] == "123"
        assert result["state"]["user"] == "test"

    @pytest.mark.asyncio
    async def test_stream_workflow(self):
        """Test streaming workflow execution."""
        wizard = MockWizard()
        agent = WizardAgent(wizard, AgentConfig(name="wizard", role=AgentRole.RESEARCHER))

        workflow_config = AgentGraphConfig(name="streaming_workflow")
        workflow = WizardWorkflow(workflow_config, [agent])

        events = []
        async for event in workflow.stream("test input"):
            events.append(event)

        # Should have start, output, and end events
        assert any(e["event"] == "wizard_start" for e in events)
        assert any(e["event"] == "wizard_output" for e in events)
        assert any(e["event"] == "wizard_end" for e in events)


# =============================================================================
# WizardAdapter Tests
# =============================================================================


class TestWizardAdapter:
    """Tests for WizardAdapter class."""

    def test_init_default(self):
        """Test adapter initialization with defaults."""
        adapter = WizardAdapter()

        assert adapter.provider == "anthropic"
        assert adapter.api_key is None

    def test_init_custom(self):
        """Test adapter initialization with custom values."""
        adapter = WizardAdapter(provider="openai", api_key="test-key")

        assert adapter.provider == "openai"
        assert adapter.api_key == "test-key"

    def test_framework_name(self):
        """Test framework_name property."""
        adapter = WizardAdapter()

        assert adapter.framework_name == "wizard"

    def test_is_available(self):
        """Test is_available method."""
        adapter = WizardAdapter()

        assert adapter.is_available() is True

    def test_create_agent(self):
        """Test create_agent with wizard in config."""
        adapter = WizardAdapter()
        wizard = MockWizard()

        config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            framework_options={"wizard": wizard},
        )

        agent = adapter.create_agent(config)

        assert isinstance(agent, WizardAgent)
        assert agent.wizard is wizard

    def test_create_agent_missing_wizard_raises(self):
        """Test create_agent raises when wizard missing."""
        adapter = WizardAdapter()

        config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
        )

        with pytest.raises(ValueError, match="Wizard instance required"):
            adapter.create_agent(config)

    def test_create_agent_from_wizard(self):
        """Test create_agent_from_wizard."""
        adapter = WizardAdapter()
        wizard = MockWizard()

        agent = adapter.create_agent_from_wizard(
            wizard,
            name="custom_name",
            role=AgentRole.REVIEWER,
            model_tier="premium",
        )

        assert isinstance(agent, WizardAgent)
        assert agent.name == "custom_name"
        assert agent.role == AgentRole.REVIEWER

    def test_create_agent_from_wizard_defaults(self):
        """Test create_agent_from_wizard with defaults."""
        adapter = WizardAdapter()
        wizard = MockWizard()

        agent = adapter.create_agent_from_wizard(wizard)

        assert agent.name == "mockwizard"  # Derived from wizard name

    def test_create_agent_from_wizard_string_role(self):
        """Test create_agent_from_wizard with string role."""
        adapter = WizardAdapter()
        wizard = MockWizard()

        agent = adapter.create_agent_from_wizard(wizard, role="researcher")

        assert agent.role == AgentRole.RESEARCHER

    def test_create_agent_from_wizard_invalid_role(self):
        """Test create_agent_from_wizard with invalid role falls back to CUSTOM."""
        adapter = WizardAdapter()
        wizard = MockWizard()

        agent = adapter.create_agent_from_wizard(wizard, role="invalid_role")

        assert agent.role == AgentRole.CUSTOM

    def test_create_agent_from_wizard_class(self):
        """Test create_agent_from_wizard_class."""
        adapter = WizardAdapter()

        agent = adapter.create_agent_from_wizard_class(
            MockWizard,
            name="class_wizard",
            wizard_kwargs={},
        )

        assert isinstance(agent, WizardAgent)
        assert agent.name == "class_wizard"

    def test_create_workflow(self):
        """Test create_workflow."""
        adapter = WizardAdapter()
        wizard = MockWizard()
        agent = WizardAgent(wizard, AgentConfig(name="wizard", role=AgentRole.RESEARCHER))

        workflow_config = AgentGraphConfig(name="test_workflow")
        workflow = adapter.create_workflow(workflow_config, [agent])

        assert isinstance(workflow, WizardWorkflow)

    def test_create_tool(self):
        """Test create_tool."""
        adapter = WizardAdapter()

        def dummy_func():
            pass

        tool = adapter.create_tool(
            name="test_tool",
            description="A test tool",
            func=dummy_func,
            args_schema={"arg": "str"},
        )

        assert tool["name"] == "test_tool"
        assert tool["description"] == "A test tool"
        assert tool["func"] is dummy_func
        assert "note" in tool


# =============================================================================
# wrap_wizard Function Tests
# =============================================================================


class TestWrapWizard:
    """Tests for wrap_wizard convenience function."""

    def test_wrap_wizard_default(self):
        """Test wrap_wizard with defaults."""
        wizard = MockWizard()

        agent = wrap_wizard(wizard)

        assert isinstance(agent, WizardAgent)
        assert agent.wizard is wizard

    def test_wrap_wizard_custom_name(self):
        """Test wrap_wizard with custom name."""
        wizard = MockWizard()

        agent = wrap_wizard(wizard, name="custom_agent")

        assert agent.name == "custom_agent"

    def test_wrap_wizard_custom_tier(self):
        """Test wrap_wizard with custom model tier."""
        wizard = MockWizard()

        agent = wrap_wizard(wizard, model_tier="premium")

        # Agent should have the tier set in config
        assert agent.config.model_tier == "premium"


class TestWizardAdapterCoverageGap:
    """Cover line 140->144: recommendations present but not a list."""

    def test_recommendations_non_list_falls_through_to_str(self):
        """Line 140->144: recs is not a list → fall through to str(result)."""
        from attune.agent_factory.adapters.wizard_adapter import WizardAgent

        # Bypass __init__ to test _extract_output directly
        agent = WizardAgent.__new__(WizardAgent)
        # 'recommendations' is a str, not a list → fall through to str(result)
        result = {"recommendations": "single rec text"}
        text = agent._extract_output(result)
        assert "recommendations" in text
