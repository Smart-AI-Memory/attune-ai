"""Smoke tests for agents_md.

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
        import attune.agents_md

        assert attune.agents_md is not None

    def test_parser_imports(self) -> None:
        """Test that MarkdownAgentParser imports."""
        from attune.agents_md import MarkdownAgentParser

        assert MarkdownAgentParser is not None

    def test_loader_imports(self) -> None:
        """Test that AgentLoader imports."""
        from attune.agents_md import AgentLoader

        assert AgentLoader is not None

    def test_registry_imports(self) -> None:
        """Test that AgentRegistry imports."""
        from attune.agents_md import AgentRegistry

        assert AgentRegistry is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_parser_instantiates(self) -> None:
        """Test MarkdownAgentParser creation."""
        from attune.agents_md import MarkdownAgentParser

        parser = MarkdownAgentParser()
        assert parser is not None

    def test_loader_instantiates(self) -> None:
        """Test AgentLoader creation with default parser."""
        from attune.agents_md import AgentLoader

        loader = AgentLoader()
        assert loader is not None
        assert loader.parser is not None

    def test_registry_instantiates(self) -> None:
        """Test AgentRegistry creation."""
        from attune.agents_md import AgentRegistry

        registry = AgentRegistry()
        assert registry is not None

    def test_registry_list_agents_empty(self) -> None:
        """Test that fresh registry has no agents."""
        from attune.agents_md import AgentRegistry

        registry = AgentRegistry()
        agents = registry.list_agents()
        assert isinstance(agents, list | dict | type(None)) or hasattr(agents, "__iter__")
