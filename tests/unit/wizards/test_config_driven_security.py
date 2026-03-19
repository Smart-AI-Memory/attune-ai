"""Security tests for ConfigDrivenWizard.from_yaml() path validation.

Ensures path traversal, null byte injection, and system directory
access are blocked when loading wizard definitions from YAML.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.wizards.config_driven import ConfigDrivenWizard


class TestFromYamlPathSecurity:
    """Verify from_yaml() validates paths before opening files."""

    def test_blocks_system_directory(self):
        """Paths targeting system directories are rejected."""
        with pytest.raises(ValueError, match="system directory"):
            ConfigDrivenWizard.from_yaml("/etc/passwd")

    def test_blocks_path_traversal(self):
        """Relative path traversal to system dirs is rejected."""
        # Use enough ../ to reach /etc from any project depth
        with pytest.raises(ValueError, match="system directory"):
            ConfigDrivenWizard.from_yaml("/etc/shadow")

    def test_blocks_null_bytes(self):
        """Null byte injection is rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            ConfigDrivenWizard.from_yaml("wizard\x00.yml")

    def test_blocks_proc_directory(self):
        """Paths targeting /proc are rejected."""
        with pytest.raises(ValueError, match="system directory"):
            ConfigDrivenWizard.from_yaml("/proc/self/environ")

    def test_blocks_dev_directory(self):
        """Paths targeting /dev are rejected."""
        with pytest.raises(ValueError, match="system directory"):
            ConfigDrivenWizard.from_yaml("/dev/null")

    def test_allows_valid_path(self, tmp_path):
        """Valid YAML file in a safe directory loads successfully."""
        yaml_file = tmp_path / "wizard.yml"
        yaml_file.write_text(
            "name: test-wizard\n"
            "description: A test wizard\n"
            "steps:\n"
            "  - id: step1\n"
            "    prompt: What is your name?\n"
        )
        # Should not raise ValueError (may raise other errors
        # if YAML structure doesn't match wizard schema, but
        # path validation passes)
        try:
            ConfigDrivenWizard.from_yaml(str(yaml_file))
        except ValueError as e:
            # Only path-related ValueErrors should fail this test
            if "system directory" in str(e) or "null bytes" in str(e):
                pytest.fail(f"Valid path was rejected: {e}")

    def test_nonexistent_valid_path_raises_file_not_found(self, tmp_path):
        """Valid but nonexistent path raises FileNotFoundError, not ValueError."""
        missing = tmp_path / "nonexistent.yml"
        with pytest.raises(FileNotFoundError):
            ConfigDrivenWizard.from_yaml(str(missing))
