"""Unit tests for wizard registry and discovery.

Tests cover:
- register_wizard / get_wizard / list_wizards
- save_custom_wizard / delete_custom_wizard
- _discover_wizards, _load_builtins, _load_custom_wizards
- Path validation for save operations
- Protection of built-in wizards from deletion

Created: 2026-02-15
"""

import pytest

from pathlib import Path
from unittest.mock import MagicMock, patch

from attune.wizards.base import BaseWizard, WizardConfig, WizardStep
from attune.wizards.session import WizardSession
from attune.prompts import PromptContext
from attune.wizards import registry


# =========================================================================
# Helpers
# =========================================================================


class FakeWizard(BaseWizard):
    """Minimal wizard for testing registration."""

    config = WizardConfig(
        wizard_id="fake",
        name="Fake Wizard",
        description="For testing",
    )
    steps = []

    def build_prompt_context(self, step):
        return PromptContext(role="test", goal="test")

    def process_step_result(self, step, result):
        pass


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry state between tests."""
    original_registry = registry._WIZARD_REGISTRY.copy()
    original_custom = registry._CUSTOM_WIZARD_INSTANCES.copy()
    original_discovered = registry._discovered
    original_custom_loaded = registry._custom_loaded

    yield

    registry._WIZARD_REGISTRY.clear()
    registry._WIZARD_REGISTRY.update(original_registry)
    registry._CUSTOM_WIZARD_INSTANCES.clear()
    registry._CUSTOM_WIZARD_INSTANCES.update(original_custom)
    registry._discovered = original_discovered
    registry._custom_loaded = original_custom_loaded


# =========================================================================
# Registration
# =========================================================================


class TestRegisterWizard:
    """Test register_wizard."""

    def test_register_and_retrieve(self):
        """Test basic registration and retrieval."""
        registry._WIZARD_REGISTRY.clear()
        registry.register_wizard("fake", FakeWizard)

        assert registry._WIZARD_REGISTRY["fake"] is FakeWizard

    def test_overwrite_existing(self):
        """Test that re-registration overwrites."""
        registry.register_wizard("fake", FakeWizard)

        class AnotherFake(FakeWizard):
            pass

        registry.register_wizard("fake", AnotherFake)
        assert registry._WIZARD_REGISTRY["fake"] is AnotherFake


# =========================================================================
# get_wizard
# =========================================================================


class TestGetWizard:
    """Test get_wizard."""

    def test_get_registered_wizard(self):
        """Test getting a wizard that's already registered."""
        registry._WIZARD_REGISTRY["fake"] = FakeWizard

        result = registry.get_wizard("fake")
        assert result is FakeWizard

    @patch.object(registry, "_discover_wizards")
    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_get_triggers_discovery(self, mock_custom, mock_builtins, mock_discover):
        """Test that get_wizard triggers discovery for unknown IDs."""
        registry._WIZARD_REGISTRY.clear()

        result = registry.get_wizard("nonexistent")

        assert result is None
        mock_discover.assert_called_once()
        mock_builtins.assert_called_once()
        mock_custom.assert_called_once()


# =========================================================================
# list_wizards
# =========================================================================


class TestListWizards:
    """Test list_wizards."""

    @patch.object(registry, "_discover_wizards")
    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_list_returns_configs(self, mock_custom, mock_builtins, mock_discover):
        """Test list_wizards returns sorted configs."""
        registry._WIZARD_REGISTRY.clear()
        registry._WIZARD_REGISTRY["fake"] = FakeWizard

        configs = registry.list_wizards()

        assert len(configs) == 1
        assert configs[0].wizard_id == "fake"
        assert configs[0].name == "Fake Wizard"

    @patch.object(registry, "_discover_wizards")
    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_list_sorts_by_id(self, mock_custom, mock_builtins, mock_discover):
        """Test configs are sorted by wizard_id."""
        registry._WIZARD_REGISTRY.clear()

        class WizardZ(FakeWizard):
            config = WizardConfig(wizard_id="zzz", name="Z", description="Z")

        class WizardA(FakeWizard):
            config = WizardConfig(wizard_id="aaa", name="A", description="A")

        registry._WIZARD_REGISTRY["zzz"] = WizardZ
        registry._WIZARD_REGISTRY["aaa"] = WizardA

        configs = registry.list_wizards()

        assert configs[0].wizard_id == "aaa"
        assert configs[1].wizard_id == "zzz"


# =========================================================================
# save_custom_wizard
# =========================================================================


class TestSaveCustomWizard:
    """Test save_custom_wizard."""

    def test_save_valid_wizard(self, tmp_path):
        """Test saving a valid custom wizard definition."""
        wizard_data = {
            "wizard_id": "my-wizard",
            "name": "My Wizard",
            "steps": [
                {"id": "q1", "step_type": "question"},
            ],
        }

        result = registry.save_custom_wizard(wizard_data, base_dir=str(tmp_path))

        assert result.exists()
        assert result.name == "my-wizard.yaml"
        assert "my-wizard" in registry._WIZARD_REGISTRY

    def test_save_invalid_schema_raises(self, tmp_path):
        """Test saving with missing required fields raises ValueError."""
        wizard_data = {"wizard_id": "bad"}  # Missing 'name' and 'steps'

        with pytest.raises(ValueError, match="missing required field"):
            registry.save_custom_wizard(wizard_data, base_dir=str(tmp_path))

    def test_save_system_dir_raises(self):
        """Test saving to system directory raises ValueError."""
        wizard_data = {
            "wizard_id": "evil",
            "name": "Evil",
            "steps": [{"id": "q1", "step_type": "question"}],
        }

        with pytest.raises(ValueError, match="Cannot write to system directory"):
            registry.save_custom_wizard(wizard_data, base_dir="/etc")


# =========================================================================
# delete_custom_wizard
# =========================================================================


class TestDeleteCustomWizard:
    """Test delete_custom_wizard."""

    def test_delete_existing_custom_wizard(self, tmp_path):
        """Test deleting an existing custom wizard."""
        # Create a YAML file
        yaml_file = tmp_path / "test-wiz.yaml"
        yaml_file.write_text("wizard_id: test-wiz\nname: Test\n")
        registry._WIZARD_REGISTRY["test-wiz"] = FakeWizard
        registry._CUSTOM_WIZARD_INSTANCES["test-wiz"] = FakeWizard()

        result = registry.delete_custom_wizard("test-wiz", base_dir=str(tmp_path))

        assert result is True
        assert not yaml_file.exists()
        assert "test-wiz" not in registry._WIZARD_REGISTRY
        assert "test-wiz" not in registry._CUSTOM_WIZARD_INSTANCES

    def test_delete_nonexistent_wizard(self, tmp_path):
        """Test deleting a wizard that doesn't exist."""
        result = registry.delete_custom_wizard("nonexistent", base_dir=str(tmp_path))

        assert result is False

    def test_delete_builtin_wizard_raises(self):
        """Test that deleting a built-in wizard raises ValueError."""
        with pytest.raises(ValueError, match="Cannot delete built-in wizard"):
            registry.delete_custom_wizard("debug")


# =========================================================================
# Discovery
# =========================================================================


class TestDiscovery:
    """Test entry-point discovery and loading."""

    def test_discover_runs_once(self):
        """Test _discover_wizards only runs once."""
        registry._discovered = False

        with patch("importlib.metadata.entry_points") as mock_eps:
            mock_eps.return_value = MagicMock()
            mock_eps.return_value.select = MagicMock(return_value=[])

            registry._discover_wizards()
            registry._discover_wizards()

            # entry_points should only be called once
            mock_eps.assert_called_once()

    def test_load_builtins(self):
        """Test _load_builtins loads built-in wizards."""
        registry._WIZARD_REGISTRY.clear()

        registry._load_builtins()

        assert "debug" in registry._WIZARD_REGISTRY
        assert "security" in registry._WIZARD_REGISTRY
        assert "refactor" in registry._WIZARD_REGISTRY
        assert "test-gen" in registry._WIZARD_REGISTRY
        assert "release-prep" in registry._WIZARD_REGISTRY

    def test_load_builtins_skips_if_already_loaded(self):
        """Test _load_builtins is idempotent."""
        registry._WIZARD_REGISTRY.clear()
        registry._WIZARD_REGISTRY["debug"] = FakeWizard  # Mark as loaded

        registry._load_builtins()

        # Should not overwrite
        assert registry._WIZARD_REGISTRY["debug"] is FakeWizard

    def test_load_custom_wizards_no_dir(self, monkeypatch):
        """Test _load_custom_wizards when directory doesn't exist."""
        registry._custom_loaded = False
        monkeypatch.setattr(registry, "CUSTOM_WIZARDS_DIR", Path("/nonexistent/dir"))

        registry._load_custom_wizards()

        assert registry._custom_loaded is True  # Marked as done even if no dir

    def test_load_custom_wizards_runs_once(self, monkeypatch):
        """Test _load_custom_wizards only runs once."""
        registry._custom_loaded = False
        monkeypatch.setattr(registry, "CUSTOM_WIZARDS_DIR", Path("/nonexistent/dir"))

        registry._load_custom_wizards()
        registry._load_custom_wizards()

        assert registry._custom_loaded is True
