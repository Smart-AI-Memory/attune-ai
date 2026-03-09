"""Smoke tests for attune.agent_factory module."""

from unittest.mock import MagicMock, patch

import pytest


class TestAgentFactoryImports:
    """Verify the agent_factory package exports are importable."""

    def test_import_package(self):
        """Test that the agent_factory package imports cleanly."""
        from attune.agent_factory import (
            AgentConfig,
            AgentFactory,
            Framework,
        )

        assert AgentFactory is not None
        assert Framework is not None
        assert AgentConfig is not None

    def test_framework_enum_values(self):
        """Test Framework enum has expected members."""
        from attune.agent_factory.framework import Framework

        assert Framework.NATIVE.value == "native"
        assert Framework.LANGCHAIN.value == "langchain"
        assert Framework.LANGGRAPH.value == "langgraph"

    def test_framework_from_string(self):
        """Test Framework.from_string conversion."""
        from attune.agent_factory.framework import Framework

        assert Framework.from_string("native") == Framework.NATIVE
        assert Framework.from_string("langchain") == Framework.LANGCHAIN

        with pytest.raises(ValueError, match="Unknown framework"):
            Framework.from_string("nonexistent")

    def test_agent_config_dataclass(self):
        """Test AgentConfig dataclass instantiation."""
        from attune.agent_factory.base import AgentConfig, AgentRole

        config = AgentConfig(
            name="test-agent",
            role=AgentRole.RESEARCHER,
            model_tier="capable",
        )
        assert config.name == "test-agent"
        assert config.role == AgentRole.RESEARCHER
        assert config.temperature == 0.7  # default

    @patch("attune.agent_factory.factory.get_recommended_framework")
    @patch("attune.agent_factory.factory.AgentFactory._get_adapter")
    def test_factory_instantiation(self, mock_adapter, mock_recommend):
        """Test AgentFactory can be instantiated with mocked adapter."""
        from attune.agent_factory.factory import AgentFactory
        from attune.agent_factory.framework import Framework

        mock_recommend.return_value = Framework.NATIVE
        mock_adapter.return_value = MagicMock()

        factory = AgentFactory()
        assert factory.framework == Framework.NATIVE
        assert factory.list_agents() == []
