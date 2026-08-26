"""Tests for empathy_llm_toolkit core modules.

Comprehensive test coverage for agent_factory/base.py, state.py, and levels.py.

Created: 2026-01-20
Coverage target: 80%+
"""

from datetime import datetime, timedelta

from attune.agent_factory.base import (
    AgentCapability,
    AgentConfig,
    AgentGraphConfig,
    AgentRole,
    BaseAdapter,
    BaseAgent,
    BaseWorkflow,
)
from attune.llm.levels import EmpathyLevel
from attune.llm.state import CollaborationState, Interaction, PatternType, UserPattern

# =============================================================================
# Agent Factory Base Tests
# =============================================================================


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_core_roles_exist(self):
        """Test that core roles are defined."""
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.WRITER.value == "writer"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.EDITOR.value == "editor"
        assert AgentRole.EXECUTOR.value == "executor"

    def test_specialized_roles_exist(self):
        """Test that specialized roles are defined."""
        assert AgentRole.DEBUGGER.value == "debugger"
        assert AgentRole.SECURITY.value == "security"
        assert AgentRole.ARCHITECT.value == "architect"
        assert AgentRole.TESTER.value == "tester"
        assert AgentRole.DOCUMENTER.value == "documenter"

    def test_rag_roles_exist(self):
        """Test that RAG roles are defined."""
        assert AgentRole.RETRIEVER.value == "retriever"
        assert AgentRole.SUMMARIZER.value == "summarizer"
        assert AgentRole.ANSWERER.value == "answerer"

    def test_custom_role_exists(self):
        """Test that custom role is defined."""
        assert AgentRole.CUSTOM.value == "custom"


class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_capabilities_exist(self):
        """Test that all capabilities are defined."""
        assert AgentCapability.CODE_EXECUTION.value == "code_execution"
        assert AgentCapability.TOOL_USE.value == "tool_use"
        assert AgentCapability.WEB_SEARCH.value == "web_search"
        assert AgentCapability.FILE_ACCESS.value == "file_access"
        assert AgentCapability.MEMORY.value == "memory"
        assert AgentCapability.RETRIEVAL.value == "retrieval"
        assert AgentCapability.VISION.value == "vision"
        assert AgentCapability.FUNCTION_CALLING.value == "function_calling"


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AgentConfig(name="test_agent")

        assert config.name == "test_agent"
        assert config.role == AgentRole.CUSTOM
        assert config.description == ""
        assert config.model_tier == "capable"
        assert config.model_override is None
        assert config.capabilities == []
        assert config.tools == []
        assert config.system_prompt is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.use_patterns is True
        assert config.track_costs is True
        assert config.memory_enabled is True
        assert config.memory_type == "conversation"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AgentConfig(
            name="custom_agent",
            role=AgentRole.RESEARCHER,
            description="A research agent",
            model_tier="premium",
            model_override="claude-opus-4-20250514",
            capabilities=[AgentCapability.WEB_SEARCH, AgentCapability.RETRIEVAL],
            temperature=0.3,
            max_tokens=8192,
        )

        assert config.name == "custom_agent"
        assert config.role == AgentRole.RESEARCHER
        assert config.description == "A research agent"
        assert config.model_tier == "premium"
        assert config.model_override == "claude-opus-4-20250514"
        assert len(config.capabilities) == 2
        assert AgentCapability.WEB_SEARCH in config.capabilities
        assert config.temperature == 0.3
        assert config.max_tokens == 8192

    def test_resilience_options(self):
        """Test resilience configuration options."""
        config = AgentConfig(
            name="resilient_agent",
            resilience_enabled=True,
            circuit_breaker_threshold=5,
            retry_max_attempts=3,
            timeout_seconds=60.0,
        )

        assert config.resilience_enabled is True
        assert config.circuit_breaker_threshold == 5
        assert config.retry_max_attempts == 3
        assert config.timeout_seconds == 60.0


class TestWorkflowConfig:
    """Tests for AgentGraphConfig dataclass."""

    def test_default_values(self):
        """Test default workflow configuration values."""
        config = AgentGraphConfig(name="test_workflow")

        assert config.name == "test_workflow"
        assert config.description == ""
        assert config.mode == "sequential"
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.state_schema is None
        assert config.checkpointing is True
        assert config.retry_on_error is True
        assert config.max_retries == 3

    def test_custom_values(self):
        """Test custom workflow configuration values."""
        config = AgentGraphConfig(
            name="custom_workflow",
            description="A custom workflow",
            mode="parallel",
            max_iterations=20,
            timeout_seconds=600,
            state_schema={"key": "value"},
            checkpointing=False,
            retry_on_error=False,
            max_retries=5,
        )

        assert config.name == "custom_workflow"
        assert config.description == "A custom workflow"
        assert config.mode == "parallel"
        assert config.max_iterations == 20
        assert config.timeout_seconds == 600
        assert config.state_schema == {"key": "value"}
        assert config.checkpointing is False
        assert config.retry_on_error is False
        assert config.max_retries == 5


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def test_concrete_implementation(self):
        """Test that we can create a concrete implementation of BaseAgent."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": f"Response to: {input_data}", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {"chunk": "Test chunk"}

        config = AgentConfig(name="concrete_agent", role=AgentRole.WRITER)
        agent = ConcreteAgent(config)

        assert agent.name == "concrete_agent"
        assert agent.role == AgentRole.WRITER
        assert agent.config == config
        assert agent._conversation_history == []

    def test_add_tool(self):
        """Test adding tools to agent."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        config = AgentConfig(name="tool_agent")
        agent = ConcreteAgent(config)

        tool = {"name": "test_tool", "func": lambda x: x}
        agent.add_tool(tool)

        assert tool in agent.config.tools
        assert len(agent.config.tools) == 1

    def test_conversation_history(self):
        """Test conversation history management."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        config = AgentConfig(name="history_agent")
        agent = ConcreteAgent(config)

        # Add to history
        agent._conversation_history.append({"role": "user", "content": "Hello"})
        agent._conversation_history.append({"role": "assistant", "content": "Hi!"})

        # Get copy of history
        history = agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"

        # Clear history
        agent.clear_history()
        assert len(agent._conversation_history) == 0

        # Original copy should be unchanged
        assert len(history) == 2

    def test_model_property(self):
        """Test model property."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        # Test with tier
        config1 = AgentConfig(name="tier_agent", model_tier="premium")
        agent1 = ConcreteAgent(config1)
        assert agent1.model == "tier:premium"

        # Test with override
        config2 = AgentConfig(
            name="override_agent",
            model_tier="cheap",
            model_override="claude-opus-4-20250514",
        )
        agent2 = ConcreteAgent(config2)
        assert agent2.model == "claude-opus-4-20250514"


class TestBaseWorkflow:
    """Tests for BaseWorkflow abstract class."""

    def test_concrete_implementation(self):
        """Test that we can create a concrete implementation of BaseWorkflow."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        class ConcreteWorkflow(BaseWorkflow):
            async def run(self, input_data, initial_state=None):
                return {"output": "workflow complete", "metadata": {}}

            async def stream(self, input_data, initial_state=None):
                yield {"step": "test"}

        config = AgentGraphConfig(name="test_workflow")
        agent1 = ConcreteAgent(AgentConfig(name="agent1"))
        agent2 = ConcreteAgent(AgentConfig(name="agent2"))

        workflow = ConcreteWorkflow(config, [agent1, agent2])

        assert workflow.config == config
        assert "agent1" in workflow.agents
        assert "agent2" in workflow.agents
        assert workflow._state == {}

    def test_get_state(self):
        """Test getting workflow state."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        class ConcreteWorkflow(BaseWorkflow):
            async def run(self, input_data, initial_state=None):
                return {}

            async def stream(self, input_data, initial_state=None):
                yield {}

        config = AgentGraphConfig(name="state_workflow")
        workflow = ConcreteWorkflow(config, [])

        workflow._state = {"key": "value"}
        state = workflow.get_state()

        assert state == {"key": "value"}
        # Should be a copy
        state["key"] = "modified"
        assert workflow._state["key"] == "value"

    def test_get_agent(self):
        """Test getting agent by name."""

        class ConcreteAgent(BaseAgent):
            async def invoke(self, input_data, context=None):
                return {"output": "test", "metadata": {}}

            async def stream(self, input_data, context=None):
                yield {}

        class ConcreteWorkflow(BaseWorkflow):
            async def run(self, input_data, initial_state=None):
                return {}

            async def stream(self, input_data, initial_state=None):
                yield {}

        config = AgentGraphConfig(name="agent_workflow")
        agent = ConcreteAgent(AgentConfig(name="my_agent"))
        workflow = ConcreteWorkflow(config, [agent])

        found_agent = workflow.get_agent("my_agent")
        assert found_agent == agent

        not_found = workflow.get_agent("nonexistent")
        assert not_found is None


class TestBaseAdapter:
    """Tests for BaseAdapter abstract class."""

    def test_concrete_implementation(self):
        """Test that we can create a concrete implementation of BaseAdapter."""

        class ConcreteAdapter(BaseAdapter):
            @property
            def framework_name(self):
                return "test_framework"

            def is_available(self):
                return True

            def create_agent(self, config):
                return None  # Simplified

            def create_workflow(self, config, agents):
                return None  # Simplified

        adapter = ConcreteAdapter()

        assert adapter.framework_name == "test_framework"
        assert adapter.is_available() is True

    def test_create_tool_default(self):
        """Test default tool creation."""

        class ConcreteAdapter(BaseAdapter):
            @property
            def framework_name(self):
                return "test"

            def is_available(self):
                return True

            def create_agent(self, config):
                return None

            def create_workflow(self, config, agents):
                return None

        adapter = ConcreteAdapter()
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

    def test_get_model_for_tier_fallback(self):
        """Test model tier resolution with fallback."""

        class ConcreteAdapter(BaseAdapter):
            @property
            def framework_name(self):
                return "test"

            def is_available(self):
                return True

            def create_agent(self, config):
                return None

            def create_workflow(self, config, agents):
                return None

        adapter = ConcreteAdapter()

        # These should work with fallback defaults
        cheap_model = adapter.get_model_for_tier("cheap", "anthropic")
        assert "haiku" in cheap_model or "claude" in cheap_model

        capable_model = adapter.get_model_for_tier("capable", "anthropic")
        assert "sonnet" in capable_model or "claude" in capable_model


# =============================================================================
# State Module Tests
# =============================================================================


class TestPatternType:
    """Tests for PatternType enum."""

    def test_pattern_types_exist(self):
        """Test that all pattern types are defined."""
        assert PatternType.SEQUENTIAL.value == "sequential"
        assert PatternType.TEMPORAL.value == "temporal"
        assert PatternType.CONDITIONAL.value == "conditional"
        assert PatternType.PREFERENCE.value == "preference"


class TestUserPattern:
    """Tests for UserPattern dataclass."""

    def test_creation(self):
        """Test creating a user pattern."""
        pattern = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="commit code",
            action="run tests",
            confidence=0.85,
            occurrences=10,
            last_seen=datetime.now(),
            context={"project": "empathy"},
        )

        assert pattern.pattern_type == PatternType.SEQUENTIAL
        assert pattern.trigger == "commit code"
        assert pattern.action == "run tests"
        assert pattern.confidence == 0.85
        assert pattern.occurrences == 10
        assert pattern.context["project"] == "empathy"

    def test_should_act_high_confidence_high_trust(self):
        """Test should_act with high confidence and high trust."""
        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="formatting",
            action="use black",
            confidence=0.9,
            occurrences=20,
            last_seen=datetime.now(),
        )

        # High trust (0.7) with high confidence (0.9) -> should act
        assert pattern.should_act(trust_level=0.7) is True

    def test_should_act_low_confidence(self):
        """Test should_act with low confidence."""
        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="formatting",
            action="use black",
            confidence=0.5,  # Below 0.7 threshold
            occurrences=5,
            last_seen=datetime.now(),
        )

        # Even with high trust, low confidence means don't act
        assert pattern.should_act(trust_level=0.9) is False

    def test_should_act_low_trust(self):
        """Test should_act with low trust."""
        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="formatting",
            action="use black",
            confidence=0.9,
            occurrences=20,
            last_seen=datetime.now(),
        )

        # High confidence but low trust -> don't act
        assert pattern.should_act(trust_level=0.5) is False


class TestInteraction:
    """Tests for Interaction dataclass."""

    def test_creation(self):
        """Test creating an interaction."""
        interaction = Interaction(
            timestamp=datetime.now(),
            role="user",
            content="Help me debug this code",
            empathy_level=2,
            metadata={"tokens": 10},
        )

        assert interaction.role == "user"
        assert interaction.content == "Help me debug this code"
        assert interaction.empathy_level == 2
        assert interaction.metadata["tokens"] == 10


class TestCollaborationState:
    """Tests for CollaborationState dataclass."""

    def test_creation_with_defaults(self):
        """Test creating collaboration state with defaults."""
        state = CollaborationState(user_id="user123")

        assert state.user_id == "user123"
        assert state.interactions == []
        assert state.detected_patterns == []
        assert state.trust_level == 0.5
        assert state.successful_actions == 0
        assert state.failed_actions == 0
        assert state.current_level == 1
        assert state.preferences == {}
        assert state.shared_context == {}

    def test_success_rate_no_actions(self):
        """Test success rate with no actions."""
        state = CollaborationState(user_id="user123")
        assert state.success_rate == 1.0  # Default to 100%

    def test_success_rate_with_actions(self):
        """Test success rate calculation."""
        state = CollaborationState(user_id="user123")
        state.successful_actions = 7
        state.failed_actions = 3

        assert state.success_rate == 0.7

    def test_add_interaction(self):
        """Test adding interactions."""
        state = CollaborationState(user_id="user123")

        state.add_interaction("user", "Hello", empathy_level=1)
        state.add_interaction("assistant", "Hi there!", empathy_level=2, metadata={"model": "test"})

        assert len(state.interactions) == 2
        assert state.interactions[0].role == "user"
        assert state.interactions[1].role == "assistant"
        assert state.interactions[1].metadata["model"] == "test"

        # Level history should only track assistant responses
        assert state.level_history == [2]

    def test_update_trust_success(self):
        """Test trust update on success."""
        state = CollaborationState(user_id="user123")
        initial_trust = state.trust_level

        state.update_trust("success", magnitude=1.0)

        assert state.trust_level > initial_trust
        assert state.successful_actions == 1
        assert len(state.trust_trajectory) == 1

    def test_update_trust_failure(self):
        """Test trust update on failure."""
        state = CollaborationState(user_id="user123")
        initial_trust = state.trust_level

        state.update_trust("failure", magnitude=1.0)

        assert state.trust_level < initial_trust
        assert state.failed_actions == 1
        assert len(state.trust_trajectory) == 1

    def test_update_trust_bounds(self):
        """Test that trust stays within bounds."""
        state = CollaborationState(user_id="user123")

        # Max out trust
        state.trust_level = 0.99
        state.update_trust("success", magnitude=1.0)
        assert state.trust_level <= 1.0

        # Min out trust
        state.trust_level = 0.01
        state.update_trust("failure", magnitude=1.0)
        assert state.trust_level >= 0.0

    def test_add_pattern_new(self):
        """Test adding a new pattern."""
        state = CollaborationState(user_id="user123")
        pattern = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="deploy",
            action="run tests first",
            confidence=0.8,
            occurrences=5,
            last_seen=datetime.now(),
        )

        state.add_pattern(pattern)

        assert len(state.detected_patterns) == 1
        assert state.detected_patterns[0].trigger == "deploy"

    def test_add_pattern_update_existing(self):
        """Test updating an existing pattern."""
        state = CollaborationState(user_id="user123")

        # Add initial pattern
        pattern1 = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="deploy",
            action="run tests first",
            confidence=0.7,
            occurrences=5,
            last_seen=datetime.now() - timedelta(days=1),
        )
        state.add_pattern(pattern1)

        # Update with same type and trigger
        pattern2 = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="deploy",
            action="run tests first",
            confidence=0.9,  # Higher confidence
            occurrences=10,  # More occurrences
            last_seen=datetime.now(),
        )
        state.add_pattern(pattern2)

        # Should still be only one pattern, but updated
        assert len(state.detected_patterns) == 1
        assert state.detected_patterns[0].confidence == 0.9
        assert state.detected_patterns[0].occurrences == 10

    def test_find_matching_pattern_found(self):
        """Test finding a matching pattern."""
        state = CollaborationState(user_id="user123")
        state.trust_level = 0.8  # High trust

        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="format code",
            action="use black",
            confidence=0.85,
            occurrences=15,
            last_seen=datetime.now(),
        )
        state.add_pattern(pattern)

        # Should find pattern when trigger matches
        found = state.find_matching_pattern("Please format code for me")
        assert found is not None
        assert found.action == "use black"

    def test_find_matching_pattern_not_found(self):
        """Test not finding a matching pattern."""
        state = CollaborationState(user_id="user123")

        # No patterns added
        found = state.find_matching_pattern("something unrelated")
        assert found is None

    def test_find_matching_pattern_low_trust(self):
        """Test that pattern isn't returned when trust is too low."""
        state = CollaborationState(user_id="user123")
        state.trust_level = 0.3  # Low trust

        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="format code",
            action="use black",
            confidence=0.85,
            occurrences=15,
            last_seen=datetime.now(),
        )
        state.add_pattern(pattern)

        # Pattern exists but trust too low
        found = state.find_matching_pattern("format code")
        assert found is None

    def test_get_conversation_history(self):
        """Test getting conversation history."""
        state = CollaborationState(user_id="user123")

        # Add multiple interactions
        for i in range(15):
            state.add_interaction("user", f"Message {i}", empathy_level=1)
            state.add_interaction("assistant", f"Response {i}", empathy_level=2)

        # Get last 10 turns
        history = state.get_conversation_history(max_turns=10)
        assert len(history) == 10

        # Get all
        all_history = state.get_conversation_history(max_turns=0)
        assert len(all_history) == 30  # 15 user + 15 assistant

        # With metadata
        history_with_meta = state.get_conversation_history(max_turns=5, include_metadata=True)
        assert "metadata" in history_with_meta[0]

    def test_should_progress_to_level(self):
        """Test level progression criteria."""
        state = CollaborationState(user_id="user123")

        # Level 2 always available
        assert state.should_progress_to_level(2) is True

        # Level 3 needs trust > 0.6 and patterns
        assert state.should_progress_to_level(3) is False
        state.trust_level = 0.7
        state.detected_patterns.append(
            UserPattern(
                pattern_type=PatternType.PREFERENCE,
                trigger="test",
                action="act",
                confidence=0.8,
                occurrences=5,
                last_seen=datetime.now(),
            ),
        )
        assert state.should_progress_to_level(3) is True

        # Level 4 needs trust > 0.7, interactions > 10, patterns > 2
        assert state.should_progress_to_level(4) is False
        state.trust_level = 0.8
        for i in range(12):
            state.add_interaction("user", f"msg{i}", empathy_level=1)
        state.detected_patterns.append(
            UserPattern(
                pattern_type=PatternType.SEQUENTIAL,
                trigger="test2",
                action="act2",
                confidence=0.8,
                occurrences=5,
                last_seen=datetime.now(),
            ),
        )
        state.detected_patterns.append(
            UserPattern(
                pattern_type=PatternType.TEMPORAL,
                trigger="test3",
                action="act3",
                confidence=0.8,
                occurrences=5,
                last_seen=datetime.now(),
            ),
        )
        assert state.should_progress_to_level(4) is True

        # Level 5 needs trust > 0.8
        assert state.should_progress_to_level(5) is False
        state.trust_level = 0.85
        assert state.should_progress_to_level(5) is True

    def test_get_statistics(self):
        """Test getting collaboration statistics."""
        state = CollaborationState(user_id="user123")
        state.successful_actions = 8
        state.failed_actions = 2
        state.trust_level = 0.75
        state.current_level = 3

        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="test",
            action="act",
            confidence=0.8,
            occurrences=5,
            last_seen=datetime.now(),
        )
        state.add_pattern(pattern)

        for i in range(5):
            state.add_interaction("user", f"msg{i}", empathy_level=i % 3 + 1)

        stats = state.get_statistics()

        assert stats["user_id"] == "user123"
        assert stats["total_interactions"] == 5
        assert stats["trust_level"] == 0.75
        assert stats["success_rate"] == 0.8
        assert stats["patterns_detected"] == 1
        assert stats["current_level"] == 3
        assert "session_duration" in stats
        assert "average_level" in stats


# =============================================================================
# Empathy Levels Tests
# =============================================================================


class TestEmpathyLevel:
    """Tests for EmpathyLevel enum."""

    def test_level_values(self):
        """Test that all levels have correct values."""
        assert EmpathyLevel.REACTIVE == 1
        assert EmpathyLevel.GUIDED == 2
        assert EmpathyLevel.PROACTIVE == 3
        assert EmpathyLevel.ANTICIPATORY == 4
        assert EmpathyLevel.SYSTEMS == 5

    def test_get_description(self):
        """Test level descriptions."""
        desc1 = EmpathyLevel.get_description(1)
        assert "Reactive" in desc1

        desc2 = EmpathyLevel.get_description(2)
        assert "Guided" in desc2

        desc3 = EmpathyLevel.get_description(3)
        assert "Proactive" in desc3

        desc4 = EmpathyLevel.get_description(4)
        assert "Anticipatory" in desc4

        desc5 = EmpathyLevel.get_description(5)
        assert "Systems" in desc5

        # Unknown level
        desc_unknown = EmpathyLevel.get_description(99)
        assert desc_unknown == "Unknown level"

    def test_get_system_prompt(self):
        """Test system prompts for each level."""
        for level in range(1, 6):
            prompt = EmpathyLevel.get_system_prompt(level)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert "Attune AI" in prompt

        # Level 1 prompt
        prompt1 = EmpathyLevel.get_system_prompt(1)
        assert "LEVEL 1" in prompt1
        assert "REACTIVE" in prompt1

        # Level 4 prompt
        prompt4 = EmpathyLevel.get_system_prompt(4)
        assert "LEVEL 4" in prompt4
        assert "trajectory" in prompt4.lower()

    def test_get_temperature_recommendation(self):
        """Test temperature recommendations."""
        assert EmpathyLevel.get_temperature_recommendation(1) == 0.7
        assert EmpathyLevel.get_temperature_recommendation(2) == 0.6
        assert EmpathyLevel.get_temperature_recommendation(3) == 0.5
        assert EmpathyLevel.get_temperature_recommendation(4) == 0.3
        assert EmpathyLevel.get_temperature_recommendation(5) == 0.4

        # Default for unknown level
        assert EmpathyLevel.get_temperature_recommendation(99) == 0.7

    def test_get_required_context(self):
        """Test required context for each level."""
        # Level 1 needs nothing
        ctx1 = EmpathyLevel.get_required_context(1)
        assert ctx1["conversation_history"] is False
        assert ctx1["user_patterns"] is False

        # Level 2 needs conversation history
        ctx2 = EmpathyLevel.get_required_context(2)
        assert ctx2["conversation_history"] is True
        assert ctx2["user_patterns"] is False

        # Level 3 needs patterns
        ctx3 = EmpathyLevel.get_required_context(3)
        assert ctx3["user_patterns"] is True

        # Level 4 needs trajectory
        ctx4 = EmpathyLevel.get_required_context(4)
        assert ctx4["trajectory_data"] is True

        # Level 5 needs pattern library
        ctx5 = EmpathyLevel.get_required_context(5)
        assert ctx5["pattern_library"] is True

    def test_get_max_tokens_recommendation(self):
        """Test max tokens recommendations."""
        assert EmpathyLevel.get_max_tokens_recommendation(1) == 1024
        assert EmpathyLevel.get_max_tokens_recommendation(2) == 1536
        assert EmpathyLevel.get_max_tokens_recommendation(3) == 2048
        assert EmpathyLevel.get_max_tokens_recommendation(4) == 4096
        assert EmpathyLevel.get_max_tokens_recommendation(5) == 4096

        # Default for unknown level
        assert EmpathyLevel.get_max_tokens_recommendation(99) == 1024

    def test_should_use_json_mode(self):
        """Test JSON mode recommendation."""
        assert EmpathyLevel.should_use_json_mode(1) is False
        assert EmpathyLevel.should_use_json_mode(2) is False
        assert EmpathyLevel.should_use_json_mode(3) is False
        assert EmpathyLevel.should_use_json_mode(4) is True
        assert EmpathyLevel.should_use_json_mode(5) is True

    def test_get_typical_use_cases(self):
        """Test typical use cases."""
        for level in range(1, 6):
            use_cases = EmpathyLevel.get_typical_use_cases(level)
            assert isinstance(use_cases, list)
            assert len(use_cases) > 0

        # Level 1 use cases
        cases1 = EmpathyLevel.get_typical_use_cases(1)
        assert "One-off questions" in cases1

        # Level 4 use cases
        cases4 = EmpathyLevel.get_typical_use_cases(4)
        assert any("predict" in c.lower() for c in cases4)

        # Unknown level returns empty list
        cases_unknown = EmpathyLevel.get_typical_use_cases(99)
        assert cases_unknown == []
