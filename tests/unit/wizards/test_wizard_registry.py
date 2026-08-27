"""Unit tests for wizard registry and discovery.

Tests cover:
- register_wizard / get_wizard / list_wizards
- save_custom_wizard / delete_custom_wizard
- _load_builtins, _load_custom_wizards
- Path validation for save operations
- Protection of built-in wizards from deletion

Created: 2026-02-15
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.prompts import PromptContext
from attune.wizards import registry
from attune.wizards.base import BaseWizard, WizardConfig

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
    original_custom_loaded = registry._custom_loaded

    yield

    registry._WIZARD_REGISTRY.clear()
    registry._WIZARD_REGISTRY.update(original_registry)
    registry._CUSTOM_WIZARD_INSTANCES.clear()
    registry._CUSTOM_WIZARD_INSTANCES.update(original_custom)
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

    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_get_triggers_discovery(self, mock_custom, mock_builtins):
        """Test that get_wizard triggers discovery for unknown IDs."""
        registry._WIZARD_REGISTRY.clear()

        result = registry.get_wizard("nonexistent")

        assert result is None
        mock_builtins.assert_called_once()
        mock_custom.assert_called_once()


# =========================================================================
# list_wizards
# =========================================================================


class TestListWizards:
    """Test list_wizards."""

    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_list_returns_configs(self, mock_custom, mock_builtins):
        """Test list_wizards returns sorted configs."""
        registry._WIZARD_REGISTRY.clear()
        registry._WIZARD_REGISTRY["fake"] = FakeWizard

        configs = registry.list_wizards()

        assert len(configs) == 1
        assert configs[0].wizard_id == "fake"
        assert configs[0].name == "Fake Wizard"

    @patch.object(registry, "_load_builtins")
    @patch.object(registry, "_load_custom_wizards")
    def test_list_sorts_by_id(self, mock_custom, mock_builtins):
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

    def test_save_permission_error_raises(self, tmp_path):
        """Test save_custom_wizard raises PermissionError on write failure."""
        from pathlib import Path
        from unittest.mock import patch as _patch

        wizard_data = {
            "wizard_id": "perm-fail",
            "name": "Perm Fail",
            "steps": [{"id": "q1", "step_type": "question"}],
        }

        with _patch.object(Path, "open", side_effect=PermissionError("read-only filesystem")):
            with pytest.raises(PermissionError, match="read-only filesystem"):
                registry.save_custom_wizard(wizard_data, base_dir=str(tmp_path))

    def test_save_os_error_raises_value_error(self, tmp_path):
        """Test save_custom_wizard wraps OSError as ValueError."""
        from pathlib import Path
        from unittest.mock import patch as _patch

        wizard_data = {
            "wizard_id": "os-fail",
            "name": "OS Fail",
            "steps": [{"id": "q1", "step_type": "question"}],
        }

        with _patch.object(Path, "open", side_effect=OSError("disk full")):
            with pytest.raises(ValueError, match="Cannot write wizard YAML"):
                registry.save_custom_wizard(wizard_data, base_dir=str(tmp_path))


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
    """Test builtin/custom wizard loading."""

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


# =========================================================================
# save_custom_wizard YAML round-trip
# =========================================================================


class TestSaveCustomWizardRoundTrip:
    """Test save_custom_wizard writes valid YAML and registers the wizard."""

    def test_save_creates_yaml_and_registers(self, tmp_path):
        """Test save writes YAML that can be read back."""
        wizard_data = {
            "wizard_id": "round-trip",
            "name": "Round Trip Wizard",
            "steps": [
                {"id": "q1", "step_type": "question"},
            ],
        }

        result_path = registry.save_custom_wizard(wizard_data, base_dir=str(tmp_path))

        assert result_path.exists()
        # Read it back
        import yaml

        with result_path.open() as f:
            loaded = yaml.safe_load(f)
        assert loaded["wizard_id"] == "round-trip"
        assert loaded["name"] == "Round Trip Wizard"
        assert len(loaded["steps"]) == 1

        # Verify registration
        assert "round-trip" in registry._WIZARD_REGISTRY
        assert "round-trip" in registry._CUSTOM_WIZARD_INSTANCES

    def test_save_creates_target_dir(self, tmp_path):
        """Test save creates the target directory if it doesn't exist."""
        nested_dir = tmp_path / "deep" / "nested"
        wizard_data = {
            "wizard_id": "nested-wiz",
            "name": "Nested",
            "steps": [{"id": "s1", "step_type": "question"}],
        }

        result_path = registry.save_custom_wizard(wizard_data, base_dir=str(nested_dir))

        assert result_path.exists()
        assert nested_dir.exists()


# =========================================================================
# delete_custom_wizard with file present
# =========================================================================


class TestDeleteCustomWizardFull:
    """Test delete_custom_wizard full flow including file removal."""

    def test_delete_removes_file_and_both_registries(self, tmp_path):
        """Test delete removes YAML file and both registry entries."""
        # Setup: create file and register in both registries
        yaml_file = tmp_path / "del-me.yaml"
        yaml_file.write_text("wizard_id: del-me\nname: Delete Me\n")
        registry._WIZARD_REGISTRY["del-me"] = FakeWizard
        registry._CUSTOM_WIZARD_INSTANCES["del-me"] = FakeWizard()

        result = registry.delete_custom_wizard("del-me", base_dir=str(tmp_path))

        assert result is True
        assert not yaml_file.exists()
        assert "del-me" not in registry._WIZARD_REGISTRY
        assert "del-me" not in registry._CUSTOM_WIZARD_INSTANCES

    def test_delete_registry_only_no_file(self, tmp_path):
        """Test delete cleans registries even when no YAML file exists."""
        registry._WIZARD_REGISTRY["ghost"] = FakeWizard
        registry._CUSTOM_WIZARD_INSTANCES["ghost"] = FakeWizard()

        result = registry.delete_custom_wizard("ghost", base_dir=str(tmp_path))

        assert result is False  # No file was deleted
        assert "ghost" not in registry._WIZARD_REGISTRY
        assert "ghost" not in registry._CUSTOM_WIZARD_INSTANCES


# =========================================================================
# _load_custom_wizards with YAML files
# =========================================================================


class TestLoadCustomWizardsFromYaml:
    """Test _load_custom_wizards loads actual YAML files."""

    def test_loads_valid_yaml(self, tmp_path, monkeypatch):
        """Test loading a valid custom wizard YAML."""
        registry._custom_loaded = False
        registry._WIZARD_REGISTRY.clear()
        monkeypatch.setattr(registry, "CUSTOM_WIZARDS_DIR", tmp_path)

        yaml_content = {
            "wizard_id": "yaml-wiz",
            "name": "YAML Wizard",
            "description": "From YAML",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        import yaml

        (tmp_path / "yaml-wiz.yaml").write_text(yaml.safe_dump(yaml_content))

        registry._load_custom_wizards()

        assert "yaml-wiz" in registry._WIZARD_REGISTRY
        assert "yaml-wiz" in registry._CUSTOM_WIZARD_INSTANCES

    def test_skips_invalid_yaml(self, tmp_path, monkeypatch):
        """Test that broken YAML files are skipped gracefully."""
        registry._custom_loaded = False
        registry._WIZARD_REGISTRY.clear()
        monkeypatch.setattr(registry, "CUSTOM_WIZARDS_DIR", tmp_path)

        (tmp_path / "broken.yaml").write_text("{{invalid yaml content")

        registry._load_custom_wizards()

        # Should not crash
        assert registry._custom_loaded is True

    def test_does_not_overwrite_existing(self, tmp_path, monkeypatch):
        """Test that custom loading does not overwrite already-registered wizards."""
        registry._custom_loaded = False
        registry._WIZARD_REGISTRY.clear()
        registry._WIZARD_REGISTRY["yaml-wiz"] = FakeWizard  # Pre-register
        monkeypatch.setattr(registry, "CUSTOM_WIZARDS_DIR", tmp_path)

        import yaml

        yaml_content = {
            "wizard_id": "yaml-wiz",
            "name": "YAML Wizard",
            "description": "From YAML",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        (tmp_path / "yaml-wiz.yaml").write_text(yaml.safe_dump(yaml_content))

        registry._load_custom_wizards()

        # Should keep the pre-registered one
        assert registry._WIZARD_REGISTRY["yaml-wiz"] is FakeWizard
