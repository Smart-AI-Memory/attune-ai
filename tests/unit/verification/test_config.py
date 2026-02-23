"""Tests for verification configuration."""

from __future__ import annotations

from attune.verification.config import VerificationConfig


class TestVerificationConfigDefaults:
    """Test VerificationConfig default values."""

    def test_defaults(self) -> None:
        """Test default configuration values."""
        config = VerificationConfig()
        assert config.enabled is True
        assert config.strategy == "auto"
        assert config.command is None
        assert config.max_retries == 2
        assert config.timeout_seconds == 300
        assert config.fail_open is False
        assert config.working_directory is None
        assert config.correction_enabled is True
        assert config.max_corrections == 2
        assert config.correction_context_chars == 8000

    def test_from_dict_empty(self) -> None:
        """Test from_dict with empty dict uses defaults."""
        config = VerificationConfig.from_dict({})
        assert config.enabled is True
        assert config.strategy == "auto"
        assert config.max_retries == 2
        assert config.correction_enabled is True
        assert config.correction_context_chars == 8000

    def test_from_dict_custom_values(self) -> None:
        """Test from_dict with custom values."""
        config = VerificationConfig.from_dict(
            {
                "enabled": False,
                "strategy": "run-tests",
                "command": "pytest -x",
                "max_retries": 5,
                "timeout_seconds": 60,
                "fail_open": True,
                "working_directory": "/tmp",
            }
        )
        assert config.enabled is False
        assert config.strategy == "run-tests"
        assert config.command == "pytest -x"
        assert config.max_retries == 5
        assert config.timeout_seconds == 60
        assert config.fail_open is True
        assert config.working_directory == "/tmp"


class TestVerificationConfigLoadForWorkflow:
    """Test per-workflow config loading and merging."""

    def test_returns_none_when_data_is_none(self) -> None:
        """Test that None input returns None."""
        result = VerificationConfig.load_for_workflow("test", None)
        assert result is None

    def test_returns_none_when_disabled(self) -> None:
        """Test that disabled config returns None."""
        result = VerificationConfig.load_for_workflow("test", {"enabled": False})
        assert result is None

    def test_global_defaults_applied(self) -> None:
        """Test that global defaults are used."""
        result = VerificationConfig.load_for_workflow(
            "code-review",
            {
                "enabled": True,
                "max_retries": 3,
                "timeout_seconds": 60,
            },
        )
        assert result is not None
        assert result.max_retries == 3
        assert result.timeout_seconds == 60

    def test_per_workflow_overrides(self) -> None:
        """Test that per-workflow settings override global defaults."""
        result = VerificationConfig.load_for_workflow(
            "code-review",
            {
                "enabled": True,
                "strategy": "lint-check",
                "max_retries": 1,
                "workflows": {
                    "code-review": {
                        "strategy": "run-tests",
                        "max_retries": 3,
                    },
                },
            },
        )
        assert result is not None
        assert result.strategy == "run-tests"
        assert result.max_retries == 3

    def test_unknown_workflow_uses_global(self) -> None:
        """Test that unknown workflow gets global defaults."""
        result = VerificationConfig.load_for_workflow(
            "unknown-workflow",
            {
                "enabled": True,
                "strategy": "lint-check",
                "workflows": {
                    "code-review": {"strategy": "run-tests"},
                },
            },
        )
        assert result is not None
        assert result.strategy == "lint-check"

    def test_per_workflow_non_dict_ignored(self) -> None:
        """Test that non-dict per-workflow value is ignored."""
        result = VerificationConfig.load_for_workflow(
            "test",
            {
                "enabled": True,
                "workflows": {
                    "test": "invalid",
                },
            },
        )
        assert result is not None
        assert result.strategy == "auto"


class TestVerificationConfigCorrection:
    """Test correction-related config fields."""

    def test_correction_enabled_from_dict(self) -> None:
        """Test correction_enabled is parsed from dict."""
        config = VerificationConfig.from_dict(
            {
                "correction_enabled": True,
                "max_corrections": 3,
            }
        )
        assert config.correction_enabled is True
        assert config.max_corrections == 3

    def test_correction_defaults_from_dict(self) -> None:
        """Test correction fields default when not in dict."""
        config = VerificationConfig.from_dict({})
        assert config.correction_enabled is True
        assert config.max_corrections == 2
        assert config.correction_context_chars == 8000

    def test_correction_context_chars_from_dict(self) -> None:
        """Test correction_context_chars is parsed from dict."""
        config = VerificationConfig.from_dict(
            {
                "correction_context_chars": 16000,
            }
        )
        assert config.correction_context_chars == 16000

    def test_correction_per_workflow_override(self) -> None:
        """Test per-workflow override of correction settings."""
        result = VerificationConfig.load_for_workflow(
            "code-review",
            {
                "enabled": True,
                "correction_enabled": False,
                "workflows": {
                    "code-review": {
                        "correction_enabled": True,
                        "max_corrections": 1,
                    },
                },
            },
        )
        assert result is not None
        assert result.correction_enabled is True
        assert result.max_corrections == 1
