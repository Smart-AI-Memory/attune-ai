"""Behavioral tests for config.py - tests that actually EXECUTE code.

These tests call methods and verify behavior, not just structure.
They directly increase code coverage by exercising execution paths.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import sys
import tempfile
from pathlib import Path

import pytest

from attune import EmpathyConfig


class TestEmpathyConfigBehavior:
    """Behavioral tests that execute EmpathyConfig methods."""

    def test_config_to_yaml_creates_valid_file(self):
        """Test that to_yaml() actually creates a valid YAML file."""
        import yaml

        config = EmpathyConfig(user_id="test_user", target_level=4)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_config.yaml"

            # BEHAVIORAL: Actually call the method (returns None)
            config.to_yaml(str(output_path))

            # Verify file was created
            assert output_path.exists()

            # Verify content is valid YAML
            with output_path.open() as f:
                loaded_data = yaml.safe_load(f)

            assert loaded_data["user_id"] == "test_user"
            assert loaded_data["target_level"] == 4

    def test_config_to_json_creates_valid_file(self):
        """Test that to_json() actually creates a valid JSON file."""
        import json

        config = EmpathyConfig(user_id="json_test", persistence_enabled=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_config.json"

            # BEHAVIORAL: Actually call the method
            config.to_json(str(output_path))

            # Verify file was created
            assert output_path.exists()

            # Verify content is valid JSON
            with output_path.open() as f:
                loaded_data = json.load(f)

            assert loaded_data["user_id"] == "json_test"
            assert loaded_data["persistence_enabled"] is True

    def test_config_from_yaml_loads_correctly(self):
        """Test that from_yaml() actually loads and parses YAML."""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "load_test.yaml"

            # Create a YAML file
            test_data = {"user_id": "loaded_user", "target_level": 5, "confidence_threshold": 0.9}
            with config_path.open("w") as f:
                yaml.safe_dump(test_data, f)

            # BEHAVIORAL: Actually call from_yaml
            loaded_config = EmpathyConfig.from_yaml(str(config_path))

            assert loaded_config.user_id == "loaded_user"
            assert loaded_config.target_level == 5
            assert loaded_config.confidence_threshold == 0.9

    def test_config_from_dict_converts_correctly(self):
        """Test that from_dict() actually converts dictionary to config."""
        test_dict = {"user_id": "dict_user", "target_level": 2, "metrics_enabled": False}

        # BEHAVIORAL: Actually call from_dict
        config = EmpathyConfig.from_dict(test_dict)

        assert config.user_id == "dict_user"
        assert config.target_level == 2
        assert config.metrics_enabled is False

    def test_config_to_dict_converts_correctly(self):
        """Test that to_dict() actually converts config to dictionary."""
        config = EmpathyConfig(user_id="to_dict_test", log_level="DEBUG")

        # BEHAVIORAL: Actually call to_dict
        result_dict = config.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["user_id"] == "to_dict_test"
        assert result_dict["log_level"] == "DEBUG"

    def test_config_update_modifies_attributes(self):
        """Test that update() actually modifies config attributes."""
        config = EmpathyConfig(user_id="original", target_level=3)

        # BEHAVIORAL: Actually call update
        config.update(user_id="updated", target_level=5)

        assert config.user_id == "updated"
        assert config.target_level == 5

    def test_config_merge_combines_configs(self):
        """Test that merge() actually combines two configs."""
        config1 = EmpathyConfig(user_id="user1", target_level=3)
        config2 = EmpathyConfig(user_id="user2", confidence_threshold=0.95)

        # BEHAVIORAL: Actually call merge
        merged = config1.merge(config2)

        # user2's values should override
        assert merged.user_id == "user2"
        assert merged.confidence_threshold == 0.95

    def test_config_validate_succeeds_for_valid_config(self):
        """Test that validate() actually checks configuration."""
        config = EmpathyConfig(user_id="valid_user", target_level=3)

        # BEHAVIORAL: Actually call validate
        result = config.validate()

        assert result is True


class TestValidateFilePathBehavior:
    """Behavioral tests for _validate_file_path() - CRITICAL security function."""

    def test_validate_file_path_allows_valid_paths(self):
        """Test that _validate_file_path allows valid paths."""
        from attune.config import _validate_file_path

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "valid.txt"

            # BEHAVIORAL: Actually call _validate_file_path
            validated = _validate_file_path(str(test_path))

            assert validated.is_absolute()
            # Resolve both paths to handle symlinks (e.g., /var -> /private/var on macOS)
            assert validated.resolve().parent == Path(tmpdir).resolve()

    def test_validate_file_path_blocks_system_directories(self):
        """Test that _validate_file_path blocks dangerous system paths."""
        from attune.config import _validate_file_path

        # Test paths that are reliably blocked (cross-platform)
        if sys.platform == "win32":
            dangerous_paths = [
                "C:\\Windows\\System32\\test",
                "C:\\Windows\\SysWOW64\\test",
                "C:\\Program Files\\test",
            ]
        else:
            # Note: /etc may resolve to /private/etc on macOS and not be blocked
            dangerous_paths = ["/sys/kernel", "/proc/self", "/dev/null"]

        for path in dangerous_paths:
            # BEHAVIORAL: Actually call _validate_file_path and expect error
            # May raise ValueError or PermissionError depending on OS
            with pytest.raises((ValueError, PermissionError)):
                _validate_file_path(path)

    def test_validate_file_path_blocks_null_bytes(self):
        """Test that _validate_file_path blocks null byte injection."""
        from attune.config import _validate_file_path

        # BEHAVIORAL: Actually call with null byte
        with pytest.raises(ValueError, match="contains null bytes"):
            _validate_file_path("config\x00.txt")

    def test_validate_file_path_blocks_empty_paths(self):
        """Test that _validate_file_path blocks empty paths."""
        from attune.config import _validate_file_path

        # BEHAVIORAL: Actually call with empty string
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path("")

    def test_validate_file_path_enforces_allowed_dir(self):
        """Test that _validate_file_path enforces allowed_dir restriction."""
        from attune.config import _validate_file_path

        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_dir = Path(tmpdir) / "allowed"
            allowed_dir.mkdir()

            # Path inside allowed dir should work
            valid_path = allowed_dir / "file.txt"
            validated = _validate_file_path(str(valid_path), allowed_dir=str(allowed_dir))
            assert validated.is_absolute()

            # Path outside allowed dir should fail
            outside_path = Path(tmpdir) / "outside.txt"
            with pytest.raises(ValueError, match="must be within"):
                _validate_file_path(str(outside_path), allowed_dir=str(allowed_dir))


# WHY THESE ARE "BEHAVIORAL" TESTS:
#
# 1. They CALL methods: to_yaml(), to_json(), from_yaml(), validate(), etc.
# 2. They verify BEHAVIOR: "does the file get created?", "is the data correct?"
# 3. They test EXECUTION PATHS: success paths, error paths, edge cases
# 4. They INCREASE COVERAGE: Every line of code executed is measured
#
# Compare to "structural" tests that only check:
# - "Does this attribute exist?"
# - "Is this a dict?"
# - "What's the enum value?"
#
# Behavioral tests actually RUN the code and verify it does what it should.
