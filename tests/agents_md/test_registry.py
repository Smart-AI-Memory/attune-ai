"""Tests for agent registry."""

import tempfile
from pathlib import Path

import pytest

from attune_llm.agents_md.registry import AgentRegistry
from attune_llm.config.unified import ModelTier, UnifiedAgentConfig


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance."""
        return AgentRegistry()

    @pytest.fixture
    def sample_config(self):
        """Create a sample agent config."""
        return UnifiedAgentConfig(
            name="test-agent",
            description="Test agent",
            role="tester",
            empathy_level=4,
        )

    def test_register_agent(self, registry, sample_config):
        """Test registering an agent."""
        registry.register(sample_config)

        assert registry.has("test-agent")
        assert registry.get("test-agent") == sample_config

    def test_register_duplicate_raises(self, registry, sample_config):
        """Test that registering duplicate name raises."""
        registry.register(sample_config)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_config)

    def test_register_duplicate_with_overwrite(self, registry, sample_config):
        """Test overwriting an existing agent."""
        registry.register(sample_config)

        new_config = UnifiedAgentConfig(
            name="test-agent",
            description="Updated",
        )
        registry.register(new_config, overwrite=True)

        assert registry.get("test-agent").description == "Updated"

    def test_unregister_agent(self, registry, sample_config):
        """Test unregistering an agent."""
        registry.register(sample_config)

        assert registry.unregister("test-agent") is True
        assert registry.has("test-agent") is False

    def test_unregister_nonexistent(self, registry):
        """Test unregistering a nonexistent agent."""
        assert registry.unregister("nonexistent") is False

    def test_get_returns_none_for_missing(self, registry):
        """Test get returns None for missing agent."""
        assert registry.get("nonexistent") is None

    def test_get_required_raises_for_missing(self, registry):
        """Test get_required raises for missing agent."""
        with pytest.raises(KeyError, match="not found"):
            registry.get_required("nonexistent")

    def test_list_agents(self, registry):
        """Test listing registered agents."""
        registry.register(UnifiedAgentConfig(name="charlie"))
        registry.register(UnifiedAgentConfig(name="alice"))
        registry.register(UnifiedAgentConfig(name="bob"))

        names = registry.list_agents()

        assert names == ["alice", "bob", "charlie"]  # Sorted

    def test_iter_agents(self, registry):
        """Test iterating over agents."""
        registry.register(UnifiedAgentConfig(name="agent1"))
        registry.register(UnifiedAgentConfig(name="agent2"))

        configs = list(registry.iter_agents())

        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "agent1" in names
        assert "agent2" in names

    def test_load_from_directory(self, registry):
        """Test loading agents from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / "agent1.md").write_text(
                """---
name: agent1
---
Agent 1.
"""
            )
            (tmpdir / "agent2.md").write_text(
                """---
name: agent2
---
Agent 2.
"""
            )

            count = registry.load_from_directory(tmpdir)

            assert count == 2
            assert registry.has("agent1")
            assert registry.has("agent2")

    def test_load_from_file(self, registry):
        """Test loading a single agent file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
        ) as f:
            f.write(
                """---
name: file-agent
---
From file.
"""
            )
            f.flush()

            config = registry.load_from_file(f.name)

            assert config.name == "file-agent"
            assert registry.has("file-agent")

    def test_reload(self, registry):
        """Test reloading agents from directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            (tmpdir / "agent1.md").write_text(
                """---
name: agent1
---
Original.
"""
            )

            registry.load_from_directory(tmpdir)
            assert registry.get("agent1").system_prompt.strip() == "Original."

            # Modify the file
            (tmpdir / "agent1.md").write_text(
                """---
name: agent1
---
Updated.
"""
            )

            registry.reload()
            assert registry.get("agent1").system_prompt.strip() == "Updated."

    def test_get_by_role(self, registry):
        """Test filtering agents by role."""
        registry.register(UnifiedAgentConfig(name="a1", role="architect"))
        registry.register(UnifiedAgentConfig(name="a2", role="architect"))
        registry.register(UnifiedAgentConfig(name="r1", role="reviewer"))

        architects = registry.get_by_role("architect")

        assert len(architects) == 2
        assert all(c.role == "architect" for c in architects)

    def test_get_by_empathy_level(self, registry):
        """Test filtering agents by empathy level."""
        registry.register(UnifiedAgentConfig(name="l2", empathy_level=2))
        registry.register(UnifiedAgentConfig(name="l4", empathy_level=4))
        registry.register(UnifiedAgentConfig(name="l5", empathy_level=5))

        # Get level 4+
        high_empathy = registry.get_by_empathy_level(min_level=4)

        assert len(high_empathy) == 2
        levels = [c.empathy_level for c in high_empathy]
        assert 4 in levels
        assert 5 in levels

    def test_get_summary(self, registry):
        """Test getting registry summary."""
        registry.register(
            UnifiedAgentConfig(
                name="arch",
                role="architect",
                model_tier=ModelTier.PREMIUM,
                empathy_level=5,
            )
        )
        registry.register(
            UnifiedAgentConfig(
                name="rev",
                role="reviewer",
                model_tier=ModelTier.CAPABLE,
                empathy_level=4,
            )
        )

        summary = registry.get_summary()

        assert summary["total_agents"] == 2
        assert "arch" in summary["agent_names"]
        assert "rev" in summary["agent_names"]
        assert summary["by_role"]["architect"] == 1
        assert summary["by_role"]["reviewer"] == 1

    def test_clear(self, registry, sample_config):
        """Test clearing the registry."""
        registry.register(sample_config)
        assert len(registry.list_agents()) == 1

        registry.clear()

        assert len(registry.list_agents()) == 0

    def test_singleton_instance(self):
        """Test singleton pattern."""
        AgentRegistry.reset_instance()

        instance1 = AgentRegistry.get_instance()
        instance2 = AgentRegistry.get_instance()

        assert instance1 is instance2

        AgentRegistry.reset_instance()
