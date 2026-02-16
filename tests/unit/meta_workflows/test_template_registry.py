"""Tests for template_registry module.

Covers TemplateRegistry class and helper functions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.meta_workflows.models import (
    AgentCompositionRule,
    FormQuestion,
    FormSchema,
    MetaWorkflowTemplate,
    QuestionType,
    TierStrategy,
)
from attune.meta_workflows.template_registry import TemplateRegistry, get_default_registry


def create_test_template(template_id: str = "test-template") -> MetaWorkflowTemplate:
    """Create a test template for testing."""
    return MetaWorkflowTemplate(
        template_id=template_id,
        name="Test Template",
        description="A test template for unit testing",
        version="1.0.0",
        author="Test",
        tags=["test"],
        form_schema=FormSchema(
            title="Test Form",
            description="A test form",
            questions=[
                FormQuestion(
                    id="q1",
                    text="Test question?",
                    type=QuestionType.TEXT_INPUT,
                )
            ],
        ),
        agent_composition_rules=[
            AgentCompositionRule(
                role="tester",
                base_template="test-agent",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            )
        ],
    )


@pytest.mark.unit
class TestTemplateRegistryInit:
    """Tests for TemplateRegistry initialization."""

    def test_init_with_custom_dir(self, tmp_path):
        """Test initialization with custom directory."""
        storage_dir = tmp_path / "templates"
        registry = TemplateRegistry(storage_dir=str(storage_dir))

        assert registry.storage_dir == storage_dir
        assert storage_dir.exists()

    def test_init_creates_directory(self, tmp_path):
        """Test that init creates storage directory."""
        storage_dir = tmp_path / "new" / "templates"
        assert not storage_dir.exists()

        TemplateRegistry(storage_dir=str(storage_dir))

        assert storage_dir.exists()

    def test_init_with_default_dir(self):
        """Test initialization with default directory."""
        with patch.object(Path, "mkdir"):
            registry = TemplateRegistry()

        assert ".attune" in str(registry.storage_dir)
        assert "templates" in str(registry.storage_dir)


@pytest.mark.unit
class TestTemplateRegistryLoadTemplate:
    """Tests for load_template method."""

    def test_load_builtin_template(self, tmp_path):
        """Test loading a built-in template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        template = registry.load_template("release-prep")

        assert template is not None
        assert template.template_id == "release-prep"
        assert template.name  # Has a name

    def test_load_user_template(self, tmp_path):
        """Test loading a user-saved template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        # Save a template first
        test_template = create_test_template("user-template")
        registry.save_template(test_template)

        # Load it back
        loaded = registry.load_template("user-template")

        assert loaded is not None
        assert loaded.template_id == "user-template"
        assert loaded.name == "Test Template"

    def test_load_nonexistent_template(self, tmp_path):
        """Test loading a template that doesn't exist."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        template = registry.load_template("nonexistent-template")

        assert template is None

    def test_load_invalid_template_raises(self, tmp_path):
        """Test that invalid template file raises ValueError."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        # Write invalid JSON
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not valid json{{{", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid template"):
            registry.load_template("invalid")


@pytest.mark.unit
class TestTemplateRegistrySaveTemplate:
    """Tests for save_template method."""

    def test_save_template(self, tmp_path):
        """Test saving a template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        template = create_test_template()

        result_path = registry.save_template(template)

        assert result_path.exists()
        assert result_path.name == "test-template.json"

    def test_save_template_content(self, tmp_path):
        """Test saved template content is valid JSON."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        template = create_test_template()

        result_path = registry.save_template(template)
        content = json.loads(result_path.read_text())

        assert content["template_id"] == "test-template"
        assert content["name"] == "Test Template"

    def test_save_overwrites_existing(self, tmp_path):
        """Test saving overwrites existing template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        template1 = create_test_template()
        template1.description = "First version"
        registry.save_template(template1)

        template2 = create_test_template()
        template2.description = "Second version"
        registry.save_template(template2)

        loaded = registry.load_template("test-template")
        assert loaded.description == "Second version"


@pytest.mark.unit
class TestTemplateRegistryListTemplates:
    """Tests for list_templates method."""

    def test_list_includes_builtin(self, tmp_path):
        """Test that list includes built-in templates."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        templates = registry.list_templates(include_builtin=True)

        assert "release-prep" in templates
        assert len(templates) >= 1

    def test_list_excludes_builtin(self, tmp_path):
        """Test that list can exclude built-in templates."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        templates = registry.list_templates(include_builtin=False)

        assert "release-prep" not in templates

    def test_list_includes_user_templates(self, tmp_path):
        """Test that list includes user templates."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        registry.save_template(create_test_template("my-custom-template"))

        templates = registry.list_templates(include_builtin=False)

        assert "my-custom-template" in templates

    def test_list_sorted(self, tmp_path):
        """Test that list is sorted alphabetically."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        registry.save_template(create_test_template("z-template"))
        registry.save_template(create_test_template("a-template"))

        templates = registry.list_templates(include_builtin=False)

        assert templates == sorted(templates)


@pytest.mark.unit
class TestTemplateRegistryIsBuiltin:
    """Tests for is_builtin method."""

    def test_builtin_template(self, tmp_path):
        """Test that built-in template returns True."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        assert registry.is_builtin("release-prep") is True

    def test_user_template(self, tmp_path):
        """Test that user template returns False."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        registry.save_template(create_test_template("user-template"))

        assert registry.is_builtin("user-template") is False

    def test_nonexistent_template(self, tmp_path):
        """Test that nonexistent template returns False."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        assert registry.is_builtin("nonexistent") is False


@pytest.mark.unit
class TestTemplateRegistryGetInfo:
    """Tests for get_template_info method."""

    def test_get_info_builtin(self, tmp_path):
        """Test getting info for built-in template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        info = registry.get_template_info("release-prep")

        assert info is not None
        assert info["template_id"] == "release-prep"
        assert "name" in info
        assert "description" in info
        assert "question_count" in info
        assert "agent_rule_count" in info

    def test_get_info_user_template(self, tmp_path):
        """Test getting info for user template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        registry.save_template(create_test_template())

        info = registry.get_template_info("test-template")

        assert info["template_id"] == "test-template"
        assert info["question_count"] == 1
        assert info["agent_rule_count"] == 1

    def test_get_info_nonexistent(self, tmp_path):
        """Test getting info for nonexistent template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        info = registry.get_template_info("nonexistent")

        assert info is None


@pytest.mark.unit
class TestTemplateRegistryDelete:
    """Tests for delete_template method."""

    def test_delete_user_template(self, tmp_path):
        """Test deleting a user template."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))
        registry.save_template(create_test_template())

        result = registry.delete_template("test-template")

        assert result is True
        assert registry.load_template("test-template") is None

    def test_delete_nonexistent(self, tmp_path):
        """Test deleting nonexistent template returns False."""
        registry = TemplateRegistry(storage_dir=str(tmp_path))

        result = registry.delete_template("nonexistent")

        assert result is False


@pytest.mark.unit
class TestGetDefaultRegistry:
    """Tests for get_default_registry function."""

    def test_returns_registry(self):
        """Test that get_default_registry returns a TemplateRegistry."""
        with patch.object(Path, "mkdir"):
            registry = get_default_registry()

        assert isinstance(registry, TemplateRegistry)
