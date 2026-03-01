"""Tests for workflow migration system.

Tests environment-aware workflow migration with config-driven preferences.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest

from attune.workflows.migration import (
    MIGRATION_MODE_AUTO,
    MIGRATION_MODE_LEGACY,
    MIGRATION_MODE_PROMPT,
    WORKFLOW_ALIASES,
    MigrationConfig,
    get_canonical_workflow_name,
    is_interactive,
    list_migrations,
    resolve_workflow_migration,
)


class TestMigrationConfig:
    """Tests for MigrationConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MigrationConfig()
        assert config.mode == MIGRATION_MODE_PROMPT
        assert config.remembered_choices == {}
        assert config.show_tips is True

    def test_load_missing_file(self, tmp_path, monkeypatch):
        """Test loading config when file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config = MigrationConfig.load()
        assert config.mode == MIGRATION_MODE_PROMPT

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Test saving and loading config."""
        monkeypatch.chdir(tmp_path)

        # Save config
        config = MigrationConfig(
            mode=MIGRATION_MODE_AUTO,
            remembered_choices={"test-gen-behavioral": "new"},
            show_tips=False,
        )
        config.save()

        # Verify file exists
        config_path = tmp_path / ".attune" / "migration.json"
        assert config_path.exists()

        # Load and verify
        loaded = MigrationConfig.load()
        assert loaded.mode == MIGRATION_MODE_AUTO
        assert loaded.remembered_choices == {"test-gen-behavioral": "new"}
        assert loaded.show_tips is False

    def test_remember_choice(self, tmp_path, monkeypatch):
        """Test remembering user choices."""
        monkeypatch.chdir(tmp_path)

        config = MigrationConfig()
        config.remember_choice("pro-review", "new")

        assert config.remembered_choices["pro-review"] == "new"

        # Verify persisted
        loaded = MigrationConfig.load()
        assert loaded.remembered_choices["pro-review"] == "new"


class TestIsInteractive:
    """Tests for is_interactive() function."""

    def test_ci_environment(self, monkeypatch):
        """Test detection of CI environments."""
        # GitHub Actions
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert is_interactive() is False

    def test_gitlab_ci(self, monkeypatch):
        """Test GitLab CI detection."""
        monkeypatch.setenv("GITLAB_CI", "true")
        assert is_interactive() is False

    def test_explicit_non_interactive(self, monkeypatch):
        """Test explicit non-interactive flag."""
        monkeypatch.setenv("ATTUNE_NO_INTERACTIVE", "1")
        assert is_interactive() is False

    def test_non_tty_stdin(self, monkeypatch):
        """Test non-TTY stdin detection."""
        # Clear CI env vars
        for var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI", "TRAVIS"]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv("ATTUNE_NO_INTERACTIVE", raising=False)

        # Mock stdin.isatty() to return False
        with patch("sys.stdin.isatty", return_value=False):
            assert is_interactive() is False


class TestResolveWorkflowMigration:
    """Tests for resolve_workflow_migration() function."""

    def test_non_aliased_workflow(self):
        """Test that non-aliased workflows pass through unchanged."""
        name, kwargs, was_migrated = resolve_workflow_migration("code-review")
        assert name == "code-review"
        assert kwargs == {}
        assert was_migrated is False

    def test_aliased_workflow_auto_mode(self, tmp_path, monkeypatch):
        """Test aliased workflow in auto mode."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CI", "true")  # Force non-interactive

        config = MigrationConfig(mode=MIGRATION_MODE_AUTO)

        name, kwargs, was_migrated = resolve_workflow_migration(
            "test-gen-behavioral",
            config=config,
        )

        assert name == "test-gen"
        assert kwargs.get("style") == "behavioral"
        assert was_migrated is True

    def test_aliased_workflow_legacy_mode(self, tmp_path, monkeypatch):
        """Test aliased workflow in legacy mode."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CI", "true")  # Force non-interactive

        config = MigrationConfig(mode=MIGRATION_MODE_LEGACY)

        name, kwargs, was_migrated = resolve_workflow_migration(
            "test-gen-behavioral",
            config=config,
        )

        assert name == "test-gen-behavioral"
        assert kwargs == {}
        assert was_migrated is False

    def test_remembered_choice_new(self, tmp_path, monkeypatch):
        """Test using remembered 'new' choice."""
        monkeypatch.chdir(tmp_path)

        config = MigrationConfig(remembered_choices={"pro-review": "new"})

        name, kwargs, was_migrated = resolve_workflow_migration("pro-review", config=config)

        assert name == "code-review"
        assert kwargs.get("mode") == "premium"
        assert was_migrated is True

    def test_remembered_choice_legacy(self, tmp_path, monkeypatch):
        """Test using remembered 'legacy' choice."""
        monkeypatch.chdir(tmp_path)

        config = MigrationConfig(remembered_choices={"pro-review": "legacy"})

        name, kwargs, was_migrated = resolve_workflow_migration("pro-review", config=config)

        assert name == "pro-review"
        assert kwargs == {}
        assert was_migrated is True  # Was processed, just kept legacy

    def test_removed_workflow_ci(self, tmp_path, monkeypatch):
        """Test removed workflow in CI exits with error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CI", "true")

        with pytest.raises(SystemExit) as exc_info:
            resolve_workflow_migration("test5")

        assert exc_info.value.code == 1

    def test_ci_silent_aliasing(self, tmp_path, monkeypatch):
        """Test CI environment uses silent aliasing."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CI", "true")

        # Default config (prompt mode) should still auto-migrate in CI
        config = MigrationConfig(mode=MIGRATION_MODE_PROMPT)

        name, kwargs, was_migrated = resolve_workflow_migration("secure-release", config=config)

        assert name == "release-prep"
        assert kwargs.get("mode") == "secure"
        assert was_migrated is True


class TestGetCanonicalWorkflowName:
    """Tests for get_canonical_workflow_name() function."""

    def test_aliased_workflow(self):
        """Test getting canonical name for aliased workflow."""
        assert get_canonical_workflow_name("pro-review") == "code-review"
        assert get_canonical_workflow_name("test-gen-behavioral") == "test-gen"
        assert get_canonical_workflow_name("secure-release") == "release-prep"

    def test_non_aliased_workflow(self):
        """Test non-aliased workflows return same name."""
        assert get_canonical_workflow_name("code-review") == "code-review"
        assert get_canonical_workflow_name("doc-gen") == "doc-gen"

    def test_removed_workflow(self):
        """Test removed workflows return original name."""
        # Removed workflows have new_name=None, so return original
        assert get_canonical_workflow_name("test5") == "test5"


class TestListMigrations:
    """Tests for list_migrations() function."""

    def test_returns_list(self):
        """Test that list_migrations returns a list."""
        migrations = list_migrations()
        assert isinstance(migrations, list)
        assert len(migrations) > 0

    def test_migration_structure(self):
        """Test structure of migration entries."""
        migrations = list_migrations()

        for m in migrations:
            assert "old_name" in m
            assert "new_name" in m
            assert "status" in m
            assert "kwargs" in m
            assert m["status"] in ("removed", "deprecated", "consolidated")

    def test_known_migrations_included(self):
        """Test that known migrations are in the list."""
        migrations = list_migrations()
        old_names = {m["old_name"] for m in migrations}

        assert "pro-review" in old_names
        assert "test-gen-behavioral" in old_names
        assert "secure-release" in old_names
        assert "test5" in old_names


class TestWorkflowAliases:
    """Tests for WORKFLOW_ALIASES constant."""

    def test_all_aliases_have_tuple_value(self):
        """Test all aliases have proper tuple structure."""
        for old_name, value in WORKFLOW_ALIASES.items():
            assert isinstance(value, tuple), f"{old_name} should have tuple value"
            assert len(value) == 2, f"{old_name} should have (new_name, kwargs)"

            new_name, kwargs = value
            assert new_name is None or isinstance(new_name, str)
            assert isinstance(kwargs, dict)

    def test_code_review_aliases(self):
        """Test code review workflow aliases."""
        assert "pro-review" in WORKFLOW_ALIASES
        new_name, kwargs = WORKFLOW_ALIASES["pro-review"]
        assert new_name == "code-review"
        assert kwargs.get("mode") == "premium"

    def test_test_generation_aliases(self):
        """Test test generation workflow aliases."""
        aliases = [
            "test-gen-behavioral",
            "test-coverage-boost",
            "autonomous-test-gen",
            "progressive-test-gen",
        ]
        for alias in aliases:
            assert alias in WORKFLOW_ALIASES, f"{alias} should be in WORKFLOW_ALIASES"

    def test_release_aliases(self):
        """Test release workflow aliases."""
        assert "secure-release" in WORKFLOW_ALIASES
        assert "orchestrated-release-prep" in WORKFLOW_ALIASES

    def test_removed_workflows(self):
        """Test removed workflows are marked correctly."""
        assert "test5" in WORKFLOW_ALIASES
        _, kwargs = WORKFLOW_ALIASES["test5"]
        assert kwargs.get("_removed") is True

        assert "manage-docs" in WORKFLOW_ALIASES
        _, kwargs = WORKFLOW_ALIASES["manage-docs"]
        assert kwargs.get("_removed") is True
