"""Smoke tests for attune.agents_md module."""


class TestAgentsMdImports:
    """Verify the agents_md package exports are importable."""

    def test_import_package(self):
        """Test that the agents_md package imports cleanly."""
        from attune.agents_md import (
            AgentLoader,
            AgentRegistry,
            MarkdownAgentParser,
        )

        assert AgentLoader is not None
        assert AgentRegistry is not None
        assert MarkdownAgentParser is not None

    def test_parser_instantiation(self):
        """Test MarkdownAgentParser can be created."""
        from attune.agents_md.parser import MarkdownAgentParser

        parser = MarkdownAgentParser()
        assert parser is not None

    def test_registry_instantiation(self):
        """Test AgentRegistry can be created."""
        from attune.agents_md.registry import AgentRegistry

        registry = AgentRegistry()
        assert registry._agents == {}

    def test_registry_list_agents_empty(self):
        """Test listing agents on empty registry returns empty."""
        from attune.agents_md.registry import AgentRegistry

        registry = AgentRegistry()
        agents = list(registry.list_agents())
        assert agents == []

    def test_parser_model_tier_map(self):
        """Test parser has model tier mappings."""
        from attune.agents_md.parser import MarkdownAgentParser

        parser = MarkdownAgentParser()
        assert "cheap" in parser.MODEL_TIER_MAP
        assert "capable" in parser.MODEL_TIER_MAP
        assert "premium" in parser.MODEL_TIER_MAP
