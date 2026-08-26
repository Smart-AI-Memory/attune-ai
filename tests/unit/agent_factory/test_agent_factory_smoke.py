"""Smoke tests for agent_factory.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.agent_factory

        assert attune.agent_factory is not None

    def test_framework_enum_imports(self) -> None:
        """Test that Framework enum imports."""
        from attune.agent_factory import Framework

        assert Framework is not None

    def test_agent_factory_class_imports(self) -> None:
        """Test that AgentFactory class imports."""
        from attune.agent_factory import AgentFactory

        assert AgentFactory is not None

    def test_base_classes_import(self) -> None:
        """Test that base classes import."""
        from attune.agent_factory import (
            AgentCapability,
            AgentConfig,
            AgentGraphConfig,
            AgentRole,
            BaseAgent,
        )

        assert AgentCapability is not None
        assert AgentConfig is not None
        assert AgentRole is not None
        assert BaseAgent is not None
        assert AgentGraphConfig is not None


@pytest.mark.unit
class TestEnums:
    """Verify enums have expected members."""

    def test_framework_has_native(self) -> None:
        """Test Framework enum includes NATIVE."""
        from attune.agent_factory import Framework

        assert Framework.NATIVE.value == "native"

    def test_framework_from_string(self) -> None:
        """Test Framework.from_string resolves known names."""
        from attune.agent_factory import Framework

        assert Framework.from_string("native") == Framework.NATIVE
        assert Framework.from_string("langchain") == Framework.LANGCHAIN

    def test_agent_role_has_members(self) -> None:
        """Test AgentRole enum has expected members."""
        from attune.agent_factory import AgentRole

        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.CUSTOM.value == "custom"

    def test_agent_capability_has_members(self) -> None:
        """Test AgentCapability enum has expected members."""
        from attune.agent_factory import AgentCapability

        assert AgentCapability.TOOL_USE.value == "tool_use"


@pytest.mark.unit
class TestInstantiation:
    """Verify dataclasses can be instantiated."""

    def test_agent_config_defaults(self) -> None:
        """Test AgentConfig with minimal args."""
        from attune.agent_factory import AgentConfig

        config = AgentConfig(name="test-agent")
        assert config.name == "test-agent"
        assert config.model_tier == "capable"

    def test_agent_factory_creates_with_native(self) -> None:
        """Test AgentFactory instantiation with native framework."""
        from attune.agent_factory import AgentFactory, Framework

        factory = AgentFactory(framework=Framework.NATIVE)
        assert factory.framework == Framework.NATIVE
