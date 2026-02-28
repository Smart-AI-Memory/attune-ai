"""Tests for custom template registration.

Tests register_custom_template, unregister_template, and get_registry.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.orchestration.agent_templates import (
    AgentTemplate,
    get_registry,
    get_template,
    register_custom_template,
    unregister_template,
)


def _make_template(
    template_id: str = "custom_test",
    role: str = "Custom Agent",
) -> AgentTemplate:
    """Helper to create a valid AgentTemplate."""
    return AgentTemplate(
        id=template_id,
        role=role,
        capabilities=["custom_capability"],
        tier_preference="CAPABLE",
        tools=["custom_tool"],
        default_instructions="Custom instructions for testing.",
        quality_gates={"min_score": 70},
    )


class TestRegisterCustomTemplate:
    """Tests for register_custom_template."""

    def test_register_new_template(self) -> None:
        """Test registering a brand-new template."""
        template = _make_template("test_register_new")
        try:
            register_custom_template(template)
            assert get_template("test_register_new") is template
        finally:
            unregister_template("test_register_new")

    def test_register_overwrites_existing(self) -> None:
        """Test that custom registration can overwrite an existing template."""
        original = _make_template("test_overwrite", role="Original")
        replacement = _make_template("test_overwrite", role="Replacement")
        try:
            register_custom_template(original)
            assert get_template("test_overwrite").role == "Original"

            register_custom_template(replacement)
            assert get_template("test_overwrite").role == "Replacement"
        finally:
            unregister_template("test_overwrite")

    def test_register_invalid_template_raises(self) -> None:
        """Test that an invalid template raises ValueError."""
        with pytest.raises(ValueError):
            register_custom_template(
                AgentTemplate(
                    id="",  # Invalid: empty id
                    role="Bad",
                    capabilities=["cap"],
                    tier_preference="CAPABLE",
                    tools=["tool"],
                    default_instructions="Instructions",
                    quality_gates={},
                ),
            )


class TestUnregisterTemplate:
    """Tests for unregister_template."""

    def test_unregister_existing(self) -> None:
        """Test removing a registered template."""
        template = _make_template("test_unregister_existing")
        register_custom_template(template)
        assert get_template("test_unregister_existing") is not None

        result = unregister_template("test_unregister_existing")
        assert result is True
        assert get_template("test_unregister_existing") is None

    def test_unregister_nonexistent(self) -> None:
        """Test removing a template that doesn't exist."""
        result = unregister_template("totally_fake_template_id")
        assert result is False

    def test_double_unregister(self) -> None:
        """Test that unregistering twice returns False the second time."""
        template = _make_template("test_double_unreg")
        register_custom_template(template)

        assert unregister_template("test_double_unreg") is True
        assert unregister_template("test_double_unreg") is False


class TestGetRegistry:
    """Tests for get_registry."""

    def test_returns_dict(self) -> None:
        """Test that get_registry returns a dict."""
        registry = get_registry()
        assert isinstance(registry, dict)

    def test_contains_builtin_templates(self) -> None:
        """Test that the registry contains pre-built templates."""
        registry = get_registry()
        # There should be at least 13 built-in templates
        assert len(registry) >= 13

        expected_ids = {
            "test_coverage_analyzer",
            "security_auditor",
            "code_reviewer",
            "documentation_writer",
            "performance_optimizer",
            "architecture_analyst",
            "refactoring_specialist",
            "test_generator",
            "test_validator",
            "report_generator",
            "documentation_analyst",
            "synthesizer",
            "generic_agent",
        }
        assert expected_ids.issubset(registry.keys())

    def test_registry_is_snapshot(self) -> None:
        """Test that get_registry returns a copy, not the live registry."""
        registry = get_registry()
        original_len = len(registry)

        # Mutating the snapshot should not affect the real registry
        registry["fake_template"] = _make_template("fake")
        assert len(get_registry()) == original_len

    def test_custom_template_appears_in_registry(self) -> None:
        """Test that registered custom templates appear in get_registry."""
        template = _make_template("test_registry_visible")
        try:
            register_custom_template(template)
            registry = get_registry()
            assert "test_registry_visible" in registry
            assert registry["test_registry_visible"].role == "Custom Agent"
        finally:
            unregister_template("test_registry_visible")
