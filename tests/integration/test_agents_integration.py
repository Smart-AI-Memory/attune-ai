"""Integration tests for the agents_md module.

Tests markdown agent parsing, loading, and registry functionality
with integration to other framework components.
"""

from textwrap import dedent

import pytest

from attune_llm.agents_md import AgentLoader, AgentRegistry, MarkdownAgentParser
from attune_llm.config.unified import UnifiedAgentConfig


class TestMarkdownAgentParserIntegration:
    """Test MarkdownAgentParser integration."""

    def test_parse_complete_agent_file(self, tmp_path):
        """Test parsing a complete agent markdown file."""
        agent_md = dedent(
            """
            ---
            name: code-reviewer
            description: Reviews code for quality, security, and best practices
            role: reviewer
            tools:
              - Read
              - Grep
              - Glob
            model_tier: capable
            empathy_level: 3
            temperature: 0.3
            ---

            # Code Reviewer Agent

            You are an expert code reviewer.

            ## Guidelines

            - Check for security vulnerabilities
            - Verify coding standards
            - Look for performance issues
        """
        ).strip()

        agent_file = tmp_path / "code-reviewer.md"
        agent_file.write_text(agent_md)

        parser = MarkdownAgentParser()
        config = parser.parse_file(agent_file)

        assert config.name == "code-reviewer"
        assert config.description == "Reviews code for quality, security, and best practices"
        assert config.role == "reviewer"
        assert "Read" in config.tools
        assert "Grep" in config.tools
        assert "Glob" in config.tools
        assert config.empathy_level == 3
        assert "expert code reviewer" in config.system_prompt

    def test_parse_minimal_agent_file(self, tmp_path):
        """Test parsing agent with minimal fields uses defaults."""
        agent_md = dedent(
            """
            ---
            name: simple-agent
            description: A simple agent
            ---

            Just do the task.
        """
        ).strip()

        agent_file = tmp_path / "simple-agent.md"
        agent_file.write_text(agent_md)

        parser = MarkdownAgentParser()
        config = parser.parse_file(agent_file)

        assert config.name == "simple-agent"
        assert config.empathy_level == 4  # default is 4 in empathy framework
        assert config.tools == []  # default
        assert config.system_prompt == "Just do the task."

    def test_parse_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises appropriate error."""
        agent_md = dedent(
            """
            ---
            name: [invalid yaml
            description: broken
            ---

            Content
        """
        ).strip()

        agent_file = tmp_path / "invalid.md"
        agent_file.write_text(agent_md)

        parser = MarkdownAgentParser()
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse_file(agent_file)


class TestAgentLoaderIntegration:
    """Test AgentLoader integration."""

    @pytest.fixture
    def agents_dir(self, tmp_path):
        """Create a directory with test agent files."""
        agents = tmp_path / "agents"
        agents.mkdir()

        # Create architect agent
        (agents / "architect.md").write_text(
            dedent(
                """
            ---
            name: architect
            description: Designs system architecture
            role: architect
            model_tier: advanced
            empathy_level: 4
            ---

            You design scalable systems.
        """
            ).strip()
        )

        # Create reviewer agent
        (agents / "reviewer.md").write_text(
            dedent(
                """
            ---
            name: reviewer
            description: Reviews code quality
            role: reviewer
            model_tier: capable
            empathy_level: 3
            ---

            You review code.
        """
            ).strip()
        )

        # Create subdirectory with empathy specialist
        specialists = agents / "specialists"
        specialists.mkdir()
        (specialists / "empathy-specialist.md").write_text(
            dedent(
                """
            ---
            name: empathy-specialist
            description: Operates at Level 4+ with pattern learning
            role: specialist
            model_tier: advanced
            empathy_level: 5
            pattern_learning: true
            ---

            You anticipate needs.
        """
            ).strip()
        )

        return agents

    def test_load_directory_non_recursive(self, agents_dir):
        """Test loading agents from directory without recursion."""
        loader = AgentLoader()
        agents = loader.load_directory(agents_dir, recursive=False)

        assert len(agents) == 2
        assert "architect" in agents
        assert "reviewer" in agents
        assert "empathy-specialist" not in agents

    def test_load_directory_recursive(self, agents_dir):
        """Test loading agents recursively from subdirectories."""
        loader = AgentLoader()
        agents = loader.load_directory(agents_dir, recursive=True)

        assert len(agents) == 3
        assert "architect" in agents
        assert "reviewer" in agents
        assert "empathy-specialist" in agents

    def test_load_single_file(self, agents_dir):
        """Test loading a single agent file."""
        loader = AgentLoader()
        config = loader.load(agents_dir / "architect.md")

        assert config.name == "architect"
        assert config.role == "architect"
        assert config.empathy_level == 4


class TestAgentRegistryIntegration:
    """Test AgentRegistry integration."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton registry between tests."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    @pytest.fixture
    def sample_config(self):
        """Create a sample agent config."""
        return UnifiedAgentConfig(
            name="test-agent",
            description="Test agent",
            role="tester",
            empathy_level=3,
            system_prompt="You are a test agent.",
        )

    def test_register_and_get_agent(self, sample_config):
        """Test registering and retrieving an agent."""
        registry = AgentRegistry()
        registry.register(sample_config)

        retrieved = registry.get("test-agent")
        assert retrieved is not None
        assert retrieved.name == "test-agent"
        assert retrieved.role == "tester"

    def test_singleton_pattern(self):
        """Test that get_instance returns same instance."""
        instance1 = AgentRegistry.get_instance()
        instance2 = AgentRegistry.get_instance()

        assert instance1 is instance2

    def test_duplicate_registration_raises(self, sample_config):
        """Test that duplicate registration raises without overwrite."""
        registry = AgentRegistry()
        registry.register(sample_config)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_config)

    def test_overwrite_registration(self, sample_config):
        """Test overwrite flag allows re-registration."""
        registry = AgentRegistry()
        registry.register(sample_config)

        # Modify and re-register
        sample_config.empathy_level = 5
        registry.register(sample_config, overwrite=True)

        retrieved = registry.get("test-agent")
        assert retrieved.empathy_level == 5

    def test_unregister_agent(self, sample_config):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        registry.register(sample_config)

        assert registry.has("test-agent")
        result = registry.unregister("test-agent")

        assert result is True
        assert not registry.has("test-agent")

    def test_list_agents(self, sample_config):
        """Test listing all agents."""
        registry = AgentRegistry()

        config2 = UnifiedAgentConfig(
            name="another-agent",
            description="Another",
            role="worker",
            empathy_level=2,
            system_prompt="Test",
        )

        registry.register(sample_config)
        registry.register(config2)

        agents = registry.list_agents()
        assert sorted(agents) == ["another-agent", "test-agent"]

    def test_get_by_role(self, tmp_path):
        """Test filtering agents by role."""
        registry = AgentRegistry()

        # Create agents with different roles
        for name, role in [("agent1", "reviewer"), ("agent2", "reviewer"), ("agent3", "architect")]:
            config = UnifiedAgentConfig(
                name=name,
                description=f"A {role}",
                role=role,
                empathy_level=3,
                system_prompt="Test",
            )
            registry.register(config)

        reviewers = registry.get_by_role("reviewer")
        assert len(reviewers) == 2

        architects = registry.get_by_role("architect")
        assert len(architects) == 1

    def test_get_by_empathy_level(self):
        """Test filtering agents by empathy level."""
        registry = AgentRegistry()

        for name, level in [("low", 1), ("mid1", 3), ("mid2", 3), ("high", 5)]:
            config = UnifiedAgentConfig(
                name=name,
                description=f"Level {level} agent",
                role="agent",
                empathy_level=level,
                system_prompt="Test",
            )
            registry.register(config)

        high_empathy = registry.get_by_empathy_level(min_level=4)
        assert len(high_empathy) == 1
        assert high_empathy[0].name == "high"

        mid_range = registry.get_by_empathy_level(min_level=2, max_level=4)
        assert len(mid_range) == 2

    def test_get_summary(self, sample_config):
        """Test getting registry summary."""
        registry = AgentRegistry()
        registry.register(sample_config)

        summary = registry.get_summary()

        assert summary["total_agents"] == 1
        assert "test-agent" in summary["agent_names"]
        assert "tester" in summary["by_role"]

    def test_load_from_directory(self, tmp_path):
        """Test loading agents from directory."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        (agents_dir / "agent1.md").write_text(
            dedent(
                """
            ---
            name: loaded-agent
            description: Loaded from file
            ---
            System prompt here.
        """
            ).strip()
        )

        registry = AgentRegistry()
        count = registry.load_from_directory(agents_dir)

        assert count == 1
        assert registry.has("loaded-agent")


class TestAgentRegistryWithHooks:
    """Test agent registry integration with hooks."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton registry."""
        AgentRegistry.reset_instance()
        yield
        AgentRegistry.reset_instance()

    def test_hook_on_agent_loaded(self):
        """Test that agents can be loaded with hook notification."""
        from attune_llm.hooks.config import HookEvent
        from attune_llm.hooks.registry import HookRegistry

        hook_registry = HookRegistry()
        loaded_agents = []

        def on_agent_load(agent_name=None, **kwargs):
            if agent_name:
                loaded_agents.append(agent_name)
            return {"success": True}

        hook_registry.register(
            event=HookEvent.SESSION_START,  # Using session start as proxy
            handler=on_agent_load,
        )

        # Simulate agent load with hook
        registry = AgentRegistry()
        config = UnifiedAgentConfig(
            name="hooked-agent",
            description="Agent with hook",
            role="worker",
            empathy_level=3,
            system_prompt="Test",
        )
        registry.register(config)

        # Fire hook to simulate notification
        hook_registry.fire_sync(
            HookEvent.SESSION_START,
            {"agent_name": config.name},
        )

        assert "hooked-agent" in loaded_agents


class TestAgentConfigValidation:
    """Test agent configuration validation."""

    def test_empathy_level_range_validation(self, tmp_path):
        """Test empathy level must be in valid range."""
        from pydantic import ValidationError

        agent_md = dedent(
            """
            ---
            name: invalid-empathy
            description: Invalid empathy level
            empathy_level: 10
            ---
            Content
        """
        ).strip()

        agent_file = tmp_path / "invalid.md"
        agent_file.write_text(agent_md)

        parser = MarkdownAgentParser()
        # Should raise ValidationError for out-of-range empathy level
        with pytest.raises(ValidationError, match="less than or equal to 5"):
            parser.parse_file(agent_file)

    def test_tools_as_list_and_string(self, tmp_path):
        """Test tools can be specified as list or comma-separated."""
        # List format
        agent_md_list = dedent(
            """
            ---
            name: list-tools
            description: Tools as list
            tools:
              - Read
              - Write
            ---
            Content
        """
        ).strip()

        # String format (some parsers support this)
        agent_file = tmp_path / "list.md"
        agent_file.write_text(agent_md_list)

        parser = MarkdownAgentParser()
        config = parser.parse_file(agent_file)

        assert isinstance(config.tools, list)
        assert "Read" in config.tools
